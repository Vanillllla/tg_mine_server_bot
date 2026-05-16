from pathlib import Path
from zipfile import ZipFile

from app.models.server import ServerInstance
from app.services.file_manager import FileManagerService


def make_server(tmp_path: Path) -> ServerInstance:
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    return ServerInstance(
        id="test_server",
        display_name="Test Server",
        server_dir=str(server_dir),
        jar_file="server.jar",
    )


def test_file_manager_blocks_path_traversal(tmp_path: Path) -> None:
    server = make_server(tmp_path)

    try:
        FileManagerService().list_dir(server, "../outside")
    except ValueError as exc:
        assert str(exc) == "path_must_stay_inside_server_dir"
    else:
        raise AssertionError("path traversal was accepted")


def test_file_manager_reads_and_writes_text_files(tmp_path: Path) -> None:
    server = make_server(tmp_path)
    manager = FileManagerService()

    manager.write_text(server, "config/test.yml", "enabled: true\n")
    result = manager.read_text(server, "config/test.yml")

    assert result["content"] == "enabled: true\n"
    assert manager.list_dir(server, "config")["items"][0]["name"] == "test.yml"


def test_file_manager_creates_missing_server_root_for_root_listing(tmp_path: Path) -> None:
    server = ServerInstance(
        id="missing_root",
        display_name="Missing Root",
        server_dir=str(tmp_path / "missing"),
        jar_file="server.jar",
    )

    result = FileManagerService().list_dir(server)

    assert result == {"path": "", "items": []}
    assert Path(server.server_dir).is_dir()


def test_file_manager_builds_client_mods_archive(tmp_path: Path) -> None:
    server = make_server(tmp_path)
    manager = FileManagerService()
    manager.ensure_client_mods_dir(server)
    manager.write_text(server, "client-mods/readme.txt", "client only\n")
    archive_path = tmp_path / "client-mods.zip"

    result = manager.write_client_mods_archive(server, archive_path)

    assert result["files_count"] == 1
    with ZipFile(archive_path) as archive:
        assert archive.namelist() == ["readme.txt"]
        assert archive.read("readme.txt").decode("utf-8").replace("\r\n", "\n") == "client only\n"
