from pathlib import Path

from app.core.settings import AppSettings
from app.models.server import CreateServerInstanceRequest
from app.services.map_integration import BLUEMAP_PROVIDER_ID, DYNMAP_PROVIDER_ID, BlueMapIntegrationService
from app.services.server_instances import ServerInstanceService


def make_service(tmp_path: Path) -> tuple[ServerInstanceService, BlueMapIntegrationService]:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    instance_service = ServerInstanceService(settings)
    return instance_service, BlueMapIntegrationService(instance_service)


def create_server(
    instance_service: ServerInstanceService,
    server_id: str = "paper_server",
    server_type: str = "paper",
) -> None:
    instance_service.create_server(
        CreateServerInstanceRequest(
            id=server_id,
            display_name="Test Server",
            jar_file="server.jar",
            minecraft_version="1.20.1",
            server_type=server_type,
        )
    )


def test_server_type_to_loader() -> None:
    assert BlueMapIntegrationService.server_type_to_loader("paper") == "spigot"
    assert BlueMapIntegrationService.server_type_to_loader("purpur") == "spigot"
    assert BlueMapIntegrationService.server_type_to_loader("fabric") == "fabric"
    assert BlueMapIntegrationService.server_type_to_loader("forge") == "forge"


def test_selects_latest_compatible_provider_version() -> None:
    selected = BlueMapIntegrationService._select_provider_version(
        [
            {
                "version_number": "5.1",
                "date_published": "2024-01-01T00:00:00Z",
                "loaders": ["spigot"],
                "game_versions": ["1.20.1"],
                "files": [{"filename": "BlueMap-5.1.jar", "url": "https://example.test/old.jar"}],
            },
            {
                "version_number": "5.2",
                "date_published": "2025-01-01T00:00:00Z",
                "loaders": ["spigot"],
                "game_versions": ["1.20.1"],
                "files": [{"primary": True, "filename": "BlueMap-5.2.jar", "url": "https://example.test/new.jar"}],
            },
        ]
    )

    assert selected is not None
    assert selected.version_number == "5.2"
    assert selected.download_url == "https://example.test/new.jar"


def test_resolve_provider_version_uses_family_game_version_tags(tmp_path: Path, monkeypatch) -> None:
    instance_service, map_service = make_service(tmp_path)
    create_server(instance_service)

    def fake_fetch(provider_id, minecraft_version, loader, featured):
        assert provider_id == BLUEMAP_PROVIDER_ID
        if minecraft_version is not None:
            return []
        return [
            {
                "version_number": "5.2-spigot",
                "date_published": "2025-01-01T00:00:00Z",
                "loaders": [loader],
                "game_versions": ["1.20.x"],
                "files": [{"primary": True, "filename": "BlueMap.jar", "url": "https://example.test/BlueMap.jar"}],
            }
        ]

    monkeypatch.setattr(map_service, "_fetch_provider_versions", fake_fetch)

    provider_id, resolved = map_service.resolve_provider_version(instance_service.get_server("paper_server"))

    assert provider_id == BLUEMAP_PROVIDER_ID
    assert resolved.version_number == "5.2-spigot"


def test_resolve_provider_version_falls_back_to_dynmap_for_old_forge(tmp_path: Path, monkeypatch) -> None:
    instance_service, map_service = make_service(tmp_path)
    instance_service.create_server(
        CreateServerInstanceRequest(
            id="forge1122",
            display_name="Forge 1.12.2",
            jar_file="forge.jar",
            minecraft_version="1.12.2",
            server_type="forge",
        )
    )

    def fake_fetch(provider_id, minecraft_version, loader, featured):
        if provider_id == BLUEMAP_PROVIDER_ID:
            return []
        return [
            {
                "version_number": "3.7-beta-4",
                "date_published": "2024-01-01T00:00:00Z",
                "loaders": [loader],
                "game_versions": ["1.12.2"],
                "files": [{"primary": True, "filename": "Dynmap.jar", "url": "https://example.test/Dynmap.jar"}],
            }
        ]

    monkeypatch.setattr(map_service, "_fetch_provider_versions", fake_fetch)

    provider_id, resolved = map_service.resolve_provider_version(instance_service.get_server("forge1122"))

    assert provider_id == DYNMAP_PROVIDER_ID
    assert resolved.version_number == "3.7-beta-4"


def test_version_range_match() -> None:
    assert BlueMapIntegrationService._version_matches_minecraft_version(
        {"game_versions": ["1.20 - 1.21.11"]},
        "1.21.4",
    )


def test_install_writes_plugin_jar_and_map_settings(tmp_path: Path, monkeypatch) -> None:
    instance_service, map_service = make_service(tmp_path)
    create_server(instance_service)

    monkeypatch.setattr(
        map_service,
        "_fetch_provider_versions",
        lambda provider_id, minecraft_version, loader, featured: [
            {
                "version_number": "5.2",
                "date_published": "2025-01-01T00:00:00Z",
                "loaders": [loader],
                "game_versions": [minecraft_version],
                "files": [{"primary": True, "filename": "BlueMap.jar", "url": "https://example.test/BlueMap.jar"}],
            }
        ],
    )
    monkeypatch.setattr(map_service, "_download_file", lambda url, target: target.write_bytes(b"jar"))

    server = map_service.install("paper_server")
    server_dir = Path(server.server_dir)

    assert (server_dir / "plugins" / "BlueMap.jar").read_bytes() == b"jar"
    assert (server_dir / "plugins" / "BlueMap" / "webserver.conf").is_file()
    assert server.map.installed is True
    assert server.map.needs_restart is True
    assert server.map.web_port == 8100

    stored = instance_service.get_server("paper_server")
    assert stored.map.jar_path == "plugins/BlueMap.jar"


def test_install_writes_mod_jar_for_fabric(tmp_path: Path, monkeypatch) -> None:
    instance_service, map_service = make_service(tmp_path)
    create_server(instance_service, server_id="fabric_server", server_type="fabric")

    monkeypatch.setattr(
        map_service,
        "_fetch_provider_versions",
        lambda provider_id, minecraft_version, loader, featured: [
            {
                "version_number": "5.2",
                "date_published": "2025-01-01T00:00:00Z",
                "files": [{"primary": True, "filename": "BlueMap.jar", "url": "https://example.test/BlueMap.jar"}],
            }
        ],
    )
    monkeypatch.setattr(map_service, "_download_file", lambda url, target: target.write_bytes(b"jar"))

    server = map_service.install("fabric_server")
    server_dir = Path(server.server_dir)

    assert (server_dir / "mods" / "BlueMap.jar").is_file()
    assert (server_dir / "config" / "bluemap" / "webserver.conf").is_file()
    assert server.map.jar_path == "mods/BlueMap.jar"


def test_install_rejects_running_server(tmp_path: Path) -> None:
    instance_service, map_service = make_service(tmp_path)
    create_server(instance_service)

    try:
        map_service.install("paper_server", server_running=True)
    except RuntimeError as exc:
        assert str(exc) == "stop_server_before_installing_map"
    else:
        raise AssertionError("running server map install was accepted")


def test_install_dynmap_fallback_for_forge_1122(tmp_path: Path, monkeypatch) -> None:
    instance_service, map_service = make_service(tmp_path)
    instance_service.create_server(
        CreateServerInstanceRequest(
            id="forge1122",
            display_name="Forge 1.12.2",
            jar_file="forge.jar",
            minecraft_version="1.12.2",
            server_type="forge",
        )
    )

    def fake_fetch(provider_id, minecraft_version, loader, featured):
        if provider_id == BLUEMAP_PROVIDER_ID:
            return []
        return [
            {
                "version_number": "3.7-beta-4",
                "date_published": "2024-01-01T00:00:00Z",
                "files": [{"primary": True, "filename": "Dynmap.jar", "url": "https://example.test/Dynmap.jar"}],
            }
        ]

    monkeypatch.setattr(map_service, "_fetch_provider_versions", fake_fetch)
    monkeypatch.setattr(map_service, "_download_file", lambda url, target: target.write_bytes(b"dynmap"))

    server = map_service.install("forge1122")
    server_dir = Path(server.server_dir)

    assert server.map.provider == DYNMAP_PROVIDER_ID
    assert server.map.web_port == 8123
    assert server.map.jar_path == "mods/Dynmap.jar"
    assert (server_dir / "mods" / "Dynmap.jar").read_bytes() == b"dynmap"
    assert (server_dir / "dynmap" / "configuration.txt").is_file()

