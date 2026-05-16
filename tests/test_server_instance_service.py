from pathlib import Path

from app.core.settings import AppSettings
from app.models.server import CreateServerInstanceRequest
from app.services.server_instances import ServerInstanceService


def test_create_server_sets_first_active(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    server = service.create_server(
        CreateServerInstanceRequest(
            id="test_server",
            display_name="Test Server",
            jar_file="server.jar",
            eula_accept=True,
        )
    )

    assert server.id == "test_server"
    assert service.active_server_id == "test_server"
    assert service.get_active_server().id == "test_server"
    assert (Path(server.server_dir) / "eula.txt").read_text(encoding="utf-8") == "eula=true\n"


def test_create_server_accepts_single_character_id(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    server = service.create_server(
        CreateServerInstanceRequest(
            id="1",
            display_name="Test Server",
            jar_file="server.jar",
        )
    )

    assert server.id == "1"
    assert Path(server.server_dir).name == "1"


def test_rejects_server_dir_outside_root(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    try:
        service.create_server(
            CreateServerInstanceRequest(
                id="bad_server",
                display_name="Bad Server",
                server_dir=str(tmp_path / "outside"),
                jar_file="server.jar",
            )
        )
    except ValueError as exc:
        assert str(exc) == "server_dir_must_be_inside_servers_root"
    else:
        raise AssertionError("outside server_dir was accepted")


def test_delete_server_removes_files_when_requested(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    server = service.create_server(
        CreateServerInstanceRequest(
            id="test_server",
            display_name="Test Server",
            jar_file="server.jar",
            eula_accept=True,
        )
    )
    server_dir = Path(server.server_dir)
    (server_dir / "server.jar").write_text("jar", encoding="utf-8")

    service.delete_server("test_server")

    assert not server_dir.exists()
    assert service.get_active_server() is None


def test_set_active_server_jar_updates_core_file(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    server = service.create_server(
        CreateServerInstanceRequest(
            id="test_server",
            display_name="Test Server",
            jar_file="server.jar",
        )
    )
    server_dir = Path(server.server_dir)
    (server_dir / "server.jar").write_text("old", encoding="utf-8")
    (server_dir / "paper.jar").write_text("new", encoding="utf-8")

    updated = service.set_active_server_jar("paper.jar")

    assert updated.jar_file == "paper.jar"
    assert service.get_active_server().jar_file == "paper.jar"
