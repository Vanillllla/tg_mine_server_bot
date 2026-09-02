from pathlib import Path

from fastapi.testclient import TestClient

import app.services.server_instances as server_instances
from app.core.settings import get_settings
from app.main import app


def test_storage_route_returns_disk_and_server_sizes(tmp_path: Path, monkeypatch) -> None:
    class DiskUsage:
        total = 20_000
        used = 5_000
        free = 15_000

    monkeypatch.setenv("MC_PANEL_HOME", str(tmp_path / "mc-panel"))
    monkeypatch.setattr(server_instances.shutil, "disk_usage", lambda path: DiskUsage())
    get_settings.cache_clear()

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "change-me"},
        )
        assert login.status_code == 200
        created = client.post(
            "/api/servers",
            json={
                "id": "storage-test",
                "display_name": "Storage Test",
                "jar_file": "server.jar",
            },
        )
        assert created.status_code == 201
        server_dir = Path(created.json()["server_dir"])
        (server_dir / "server.jar").write_bytes(b"jar-data")

        response = client.get("/api/servers/storage")

    assert response.status_code == 200
    assert response.json() == {
        "total_bytes": 20_000,
        "used_bytes": 5_000,
        "free_bytes": 15_000,
        "used_percent": 25.0,
        "servers_bytes": 8,
        "servers": [{"id": "storage-test", "size_bytes": 8}],
    }
