from pathlib import Path

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
