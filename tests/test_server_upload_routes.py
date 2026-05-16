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


def test_upload_core_rejects_invalid_id_before_creating_server_dir(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    try:
        response = client.post(
            "/api/servers/upload-core",
            data={
                "id": "forge1-12-2-HBM",
                "display_name": "Bad ID",
                "java_path": "java",
                "xms_mb": "512",
                "xmx_mb": "1024",
            },
            files={"core_file": ("server.jar", b"jar-content", "application/java-archive")},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "server_id_must_be_slug"
        assert list((get_settings().servers_dir).iterdir()) == []
    finally:
        client.__exit__(None, None, None)


def test_files_without_active_server_returns_clear_error(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    try:
        response = client.get("/api/servers/active/files")

        assert response.status_code == 404
        assert response.json()["detail"] == "active_server_not_selected"
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

        files_response = client.get("/api/servers/active/files")
        assert files_response.status_code == 200
        file_names = {item["name"] for item in files_response.json()["items"]}
        assert {"server.jar", "config"}.issubset(file_names)
    finally:
        client.__exit__(None, None, None)


def test_files_upload_endpoint_writes_file_to_active_server(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    try:
        create_response = client.post(
            "/api/servers/upload-core",
            data={
                "id": "file_upload_server",
                "display_name": "File Upload Server",
                "java_path": "java",
                "xms_mb": "512",
                "xmx_mb": "1024",
            },
            files={"core_file": ("server.jar", b"jar-content", "application/java-archive")},
        )
        assert create_response.status_code == 201
        server_dir = Path(create_response.json()["server_dir"])

        upload_response = client.post(
            "/api/servers/active/files/upload",
            files={"file": ("config.txt", b"config-content", "text/plain")},
        )

        assert upload_response.status_code == 200
        assert upload_response.json()["uploaded"] is True
        assert (server_dir / "config.txt").read_bytes() == b"config-content"
    finally:
        client.__exit__(None, None, None)


def test_files_upload_endpoint_accepts_folder_upload_filename(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    try:
        create_response = client.post(
            "/api/servers/upload-core",
            data={
                "id": "folder_upload_server",
                "display_name": "Folder Upload Server",
                "java_path": "java",
                "xms_mb": "512",
                "xmx_mb": "1024",
            },
            files={"core_file": ("server.jar", b"jar-content", "application/java-archive")},
        )
        assert create_response.status_code == 201
        server_dir = Path(create_response.json()["server_dir"])

        mkdir_response = client.post(
            "/api/servers/active/files/directories",
            json={"name": "mods"},
        )
        assert mkdir_response.status_code == 200

        upload_response = client.post(
            "/api/servers/active/files/upload?path=mods",
            files={"file": ("mods/example.jar", b"mod-content", "application/java-archive")},
        )

        assert upload_response.status_code == 200
        assert upload_response.json()["uploaded"] is True
        assert (server_dir / "mods" / "example.jar").read_bytes() == b"mod-content"
        assert not (server_dir / "mods" / "mods").exists()
    finally:
        client.__exit__(None, None, None)


def test_import_archive_accepts_windows_separators(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    archive_bytes = BytesIO()
    with ZipFile(archive_bytes, "w") as archive:
        archive.writestr("pack\\nested\\server.jar", b"jar-content")
    archive_bytes.seek(0)

    try:
        response = client.post(
            "/api/servers/import-archive",
            data={
                "id": "zip_windows_paths",
                "display_name": "Zip Windows Paths",
                "java_path": "java",
                "xms_mb": "512",
                "xmx_mb": "1024",
                "jar_file": "nested\\server.jar",
            },
            files={"archive_file": ("server.zip", archive_bytes.getvalue(), "application/zip")},
        )

        assert response.status_code == 201
        body = response.json()
        server_dir = Path(body["server_dir"])
        assert body["jar_file"] == "nested/server.jar"
        assert (server_dir / "nested" / "server.jar").read_bytes() == b"jar-content"
    finally:
        client.__exit__(None, None, None)


def test_import_archive_accepts_windows_directory_entries(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    archive_bytes = BytesIO()
    with ZipFile(archive_bytes, "w") as archive:
        archive.writestr("pack\\nested\\", b"")
        archive.writestr("pack\\nested\\server.jar", b"jar-content")
    archive_bytes.seek(0)

    try:
        response = client.post(
            "/api/servers/import-archive",
            data={
                "id": "zip_windows_dirs",
                "display_name": "Zip Windows Dirs",
                "java_path": "java",
                "xms_mb": "512",
                "xmx_mb": "1024",
            },
            files={"archive_file": ("server.zip", archive_bytes.getvalue(), "application/zip")},
        )

        assert response.status_code == 201
        body = response.json()
        server_dir = Path(body["server_dir"])
        assert body["jar_file"] == "nested/server.jar"
        assert (server_dir / "nested" / "server.jar").read_bytes() == b"jar-content"
    finally:
        client.__exit__(None, None, None)


def test_import_archive_rejects_windows_absolute_paths(tmp_path: Path, monkeypatch) -> None:
    client = make_client(tmp_path, monkeypatch)
    archive_bytes = BytesIO()
    with ZipFile(archive_bytes, "w") as archive:
        archive.writestr(r"C:\server.jar", b"jar-content")
    archive_bytes.seek(0)

    try:
        response = client.post(
            "/api/servers/import-archive",
            data={
                "id": "zip_bad_path",
                "display_name": "Zip Bad Path",
                "java_path": "java",
                "xms_mb": "512",
                "xmx_mb": "1024",
            },
            files={"archive_file": ("server.zip", archive_bytes.getvalue(), "application/zip")},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "archive_contains_unsafe_path"
        assert not (get_settings().servers_dir / "zip_bad_path").exists()
    finally:
        client.__exit__(None, None, None)
