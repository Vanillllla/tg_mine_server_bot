from pathlib import Path

import pytest

import app.services.server_instances as server_instances
from app.core.json_store import write_json_atomic
from app.core.settings import AppSettings
from app.models.server import CreateServerInstanceRequest, LaunchMode, UpdateServerInstanceRequest
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


def test_get_server_adds_default_map_settings_for_legacy_payload(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    server_dir = settings.servers_dir / "legacy"
    server_dir.mkdir()
    write_json_atomic(
        settings.servers_config_path,
        {
            "legacy": {
                "display_name": "Legacy Server",
                "server_dir": str(server_dir),
                "jar_file": "server.jar",
                "minecraft_version": "1.20.1",
                "server_type": "paper",
            }
        },
    )

    server = ServerInstanceService(settings).get_server("legacy")

    assert server.map.provider == "bluemap"
    assert server.map.enabled is False
    assert server.map.installed is False


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


def test_storage_summary_reports_disk_and_each_server_size(tmp_path: Path, monkeypatch) -> None:
    class DiskUsage:
        total = 10_000
        used = 7_500
        free = 2_500

    monkeypatch.setattr(server_instances.shutil, "disk_usage", lambda path: DiskUsage())
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    first = service.create_server(
        CreateServerInstanceRequest(
            id="first",
            display_name="First Server",
            jar_file="server.jar",
        )
    )
    second = service.create_server(
        CreateServerInstanceRequest(
            id="second",
            display_name="Second Server",
            jar_file="server.jar",
        )
    )
    first_dir = Path(first.server_dir)
    second_dir = Path(second.server_dir)
    (first_dir / "server.jar").write_bytes(b"a" * 40)
    (first_dir / "world").mkdir()
    (first_dir / "world" / "region.mca").write_bytes(b"b" * 60)
    (second_dir / "server.jar").write_bytes(b"c" * 25)

    summary = service.get_storage_summary()

    assert summary.total_bytes == 10_000
    assert summary.used_bytes == 7_500
    assert summary.free_bytes == 2_500
    assert summary.used_percent == 75.0
    assert summary.servers_bytes == 125
    assert {item.id: item.size_bytes for item in summary.servers} == {
        "first": 100,
        "second": 25,
    }


def test_directory_size_does_not_follow_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "server"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "inside.dat").write_bytes(b"inside")
    (outside / "large.dat").write_bytes(b"outside-data")
    try:
        (root / "linked-outside").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this platform")

    assert ServerInstanceService._directory_size(root) == len(b"inside")


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


def test_set_active_server_jar_rejects_txt_file(tmp_path: Path) -> None:
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
    (server_dir / "server.txt").write_text("not a jar", encoding="utf-8")

    try:
        service.set_active_server_jar("server.txt")
    except ValueError as exc:
        assert str(exc) == "jar_file_must_be_jar"
    else:
        raise AssertionError("txt file was accepted as jar launch target")


def test_set_active_launch_target_accepts_forge_args_file(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    server = service.create_server(
        CreateServerInstanceRequest(
            id="forge_server",
            display_name="Forge Server",
            jar_file="server.jar",
        )
    )
    server_dir = Path(server.server_dir)
    forge_args = server_dir / "libraries" / "net" / "minecraftforge" / "forge" / "1.20.1-47.2.0" / "win_args.txt"
    forge_args.parent.mkdir(parents=True)
    forge_args.write_text("--launchTarget forge_server\n", encoding="utf-8")

    updated = service.set_active_launch_target(
        "libraries/net/minecraftforge/forge/1.20.1-47.2.0/win_args.txt",
        LaunchMode.FORGE_ARGS,
    )

    assert updated.launch_mode == LaunchMode.FORGE_ARGS
    assert updated.jar_file == "libraries/net/minecraftforge/forge/1.20.1-47.2.0/win_args.txt"


def test_find_forge_args_files_prefers_newest_version(tmp_path: Path) -> None:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    service = ServerInstanceService(settings)

    server = service.create_server(
        CreateServerInstanceRequest(
            id="forge_server",
            display_name="Forge Server",
            jar_file="server.jar",
        )
    )
    server_dir = Path(server.server_dir)
    args_name = "win_args.txt" if server_instances.os.name == "nt" else "unix_args.txt"
    old_args = server_dir / "libraries" / "net" / "minecraftforge" / "forge" / "1.19.4-45.1.0" / args_name
    new_args = server_dir / "libraries" / "net" / "minecraftforge" / "forge" / "1.20.1-47.2.0" / args_name
    old_args.parent.mkdir(parents=True)
    new_args.parent.mkdir(parents=True)
    old_args.write_text("old\n", encoding="utf-8")
    new_args.write_text("new\n", encoding="utf-8")

    matches = service.find_forge_args_files(server)

    assert matches[0] == f"libraries/net/minecraftforge/forge/1.20.1-47.2.0/{args_name}"
