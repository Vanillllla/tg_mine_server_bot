from pathlib import Path

from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.main import app
from app.services.map_integration import BlueMapIntegrationService


def make_client(tmp_path: Path, monkeypatch, login: bool = True) -> TestClient:
    monkeypatch.setenv("MC_PANEL_HOME", str(tmp_path / "mc-panel"))
    get_settings.cache_clear()
    client = TestClient(app)
    client.__enter__()
    if login:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "change-me"},
        )
        assert response.status_code == 200
    return client


def create_server(client: TestClient) -> dict:
    response = client.post(
        "/api/servers/upload-core",
        data={
            "id": "map_server",
            "display_name": "Map Server",
            "minecraft_version": "1.20.1",
            "server_type": "paper",
            "java_path": "java",
            "xms_mb": "1024",
            "xmx_mb": "1024",
        },
        files={"core_file": ("server.jar", b"jar-content", "application/java-archive")},
    )
    assert response.status_code == 201
    return response.json()


def stub_bluemap_download(monkeypatch) -> None:
    monkeypatch.setattr(
        BlueMapIntegrationService,
        "_fetch_provider_versions",
        lambda self, provider_id, minecraft_version, loader, featured: [
            {
                "version_number": "5.2",
                "date_published": "2025-01-01T00:00:00Z",
                "loaders": [loader],
                "game_versions": [minecraft_version],
                "files": [{"primary": True, "filename": "BlueMap.jar", "url": "https://example.test/BlueMap.jar"}],
            }
        ],
    )
    monkeypatch.setattr(
        BlueMapIntegrationService,
        "_download_file",
        lambda self, url, target: target.write_bytes(b"jar"),
    )


def test_admin_can_install_bluemap(tmp_path: Path, monkeypatch) -> None:
    stub_bluemap_download(monkeypatch)
    client = make_client(tmp_path, monkeypatch)
    try:
        server = create_server(client)

        response = client.post(f"/api/servers/{server['id']}/map/install", json={"provider": "bluemap"})

        assert response.status_code == 200
        body = response.json()
        assert body["installed"] is True
        assert body["status"] == "needs_restart"
        assert (Path(server["server_dir"]) / "plugins" / "BlueMap.jar").is_file()
    finally:
        client.__exit__(None, None, None)


def test_invited_user_can_view_status_but_not_install(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    try:
        server = create_server(client)
        invite = client.post("/api/auth/invite").json()
        client.post("/api/auth/logout")
        invite_login = client.post("/api/auth/invite-login", json={"token": invite["token"]})
        assert invite_login.status_code == 200

        status_response = client.get(f"/api/servers/{server['id']}/map/status")
        install_response = client.post(f"/api/servers/{server['id']}/map/install", json={"provider": "bluemap"})

        assert status_response.status_code == 200
        assert status_response.json()["status"] == "not_configured"
        assert install_response.status_code == 403
    finally:
        client.__exit__(None, None, None)


def test_map_proxy_requires_authentication(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch, login=False)
    try:
        response = client.get("/map/active/")

        assert response.status_code == 401
    finally:
        client.__exit__(None, None, None)

