from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.main import app


def make_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("MC_PANEL_HOME", str(tmp_path / "mc-panel"))
    get_settings.cache_clear()
    client = TestClient(app)
    client.__enter__()
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "change-me"},
    )
    assert response.status_code == 200
    return client


def test_upload_core_creates_server_and_writes_jar(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    try:
        response = client.post(
            "/api/servers/upload-core",
            data={
                "id": "1",
                "display_name": "Jar Server",
                "minecraft_version": "1.20.1",
                "server_type": "paper",
                "java_path": "java",
                "xms_mb": "512",
                "xmx_mb": "1024",
                "eula_accept": "true",
            },
            files={"core_file": ("server.jar", b"jar-content", "application/java-archive")},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == "1"
        assert body["jar_file"] == "server.jar"
        assert (Path(body["server_dir"]) / "server.jar").read_bytes() == b"jar-content"
        assert (Path(body["server_dir"]) / "eula.txt").read_text(encoding="utf-8") == "eula=true\n"
    finally:
        client.__exit__(None, None, None)


def test_import_archive_creates_server_and_extracts_zip(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    archive_bytes = BytesIO()
    with ZipFile(archive_bytes, "w") as archive:
        archive.writestr("pack/server.jar", b"jar-content")
        archive.writestr("pack/config/server.properties", "motd=Test\n")
    archive_bytes.seek(0)

    try:
        response = client.post(
            "/api/servers/import-archive",
            data={
                "id": "zip_server",
                "display_name": "Zip Server",
                "minecraft_version": "1.20.1",
                "server_type": "forge",
                "java_path": "java",
                "xms_mb": "512",
                "xmx_mb": "1024",
                "eula_accept": "true",
                "jar_file": "",
            },
            files={"archive_file": ("server.zip", archive_bytes.getvalue(), "application/zip")},
        )

        assert response.status_code == 201
        body = response.json()
        server_dir = Path(body["server_dir"])
        assert body["id"] == "zip_server"
        assert body["jar_file"] == "server.jar"
        assert (server_dir / "server.jar").read_bytes() == b"jar-content"
        assert (server_dir / "config" / "server.properties").read_text(encoding="utf-8") == "motd=Test\n"
    finally:
        client.__exit__(None, None, None)
