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

