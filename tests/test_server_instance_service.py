from pathlib import Path

import app.services.server_instances as server_instances
from app.core.json_store import write_json_atomic
from app.core.settings import AppSettings
from app.models.server import CreateServerInstanceRequest, UpdateServerInstanceRequest
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


def test_update_server_changes_memory_and_writes_eula(tmp_path: Path) -> None:
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

    updated = service.update_server(
        "test_server",
        UpdateServerInstanceRequest(xms_mb=1024, xmx_mb=2048, eula_accept=True),
    )

    assert updated.xms_mb == 1024
    assert updated.xmx_mb == 2048
    assert updated.eula_accept is True
    assert (Path(server.server_dir) / "eula.txt").read_text(encoding="utf-8") == "eula=true\n"


def test_memory_limit_uses_floor_host_gb_minus_reserved(tmp_path: Path, monkeypatch) -> None:
    class VirtualMemory:
        total = int(11.7 * 1024**3)

    class PsutilStub:
        @staticmethod
        def virtual_memory():
            return VirtualMemory()

    monkeypatch.setattr(server_instances, "psutil", PsutilStub)
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    server = service.create_server(
        CreateServerInstanceRequest(
            id="test_server",
            display_name="Test Server",
            jar_file="server.jar",
            xms_mb=1024,
            xmx_mb=10 * 1024,
        )
    )

    assert server.xmx_mb == 10 * 1024

    try:
        service.update_server("test_server", UpdateServerInstanceRequest(xmx_mb=11 * 1024))
    except ValueError as exc:
        assert str(exc) == "memory_exceeds_host_limit: max_10_gb"
    else:
        raise AssertionError("memory above host limit was accepted")


def test_get_server_uses_existing_eula_file(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    server = service.create_server(
        CreateServerInstanceRequest(
            id="test_server",
            display_name="Test Server",
            jar_file="server.jar",
            eula_accept=False,
        )
    )
    (Path(server.server_dir) / "eula.txt").write_text("eula=true\n", encoding="utf-8")

    assert service.get_server("test_server").eula_accept is True


def test_get_server_rebases_stale_server_dir_to_current_runtime(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    server_dir = settings.servers_dir / "legacy"
    server_dir.mkdir()
    (server_dir / "server.jar").write_text("jar", encoding="utf-8")
    write_json_atomic(
        settings.servers_config_path,
        {
            "legacy": {
                "display_name": "Legacy Server",
                "server_dir": r"C:\old\mc-panel\servers\legacy",
                "jar_file": "server.jar",
            }
        },
    )

    server = ServerInstanceService(settings).get_server("legacy")

    assert Path(server.server_dir) == server_dir.resolve()


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
