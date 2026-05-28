from io import BytesIO
from pathlib import Path

from app.core.settings import AppSettings
from app.models.mod_catalog import ModCatalogItemRequest
from app.models.server import CreateServerInstanceRequest
from app.services.mod_catalog import ModCatalogService
from app.services.server_instances import ServerInstanceService


def make_services(tmp_path: Path) -> tuple[ServerInstanceService, ModCatalogService]:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    return ServerInstanceService(settings), ModCatalogService(settings)


def test_uploaded_mod_is_copied_to_matching_server(tmp_path: Path) -> None:
    instance_service, catalog = make_services(tmp_path)
    catalog.add_uploaded_item(
        ModCatalogItemRequest(
            id="example_mod",
            display_name="Example Mod",
            server_types=["forge"],
            minecraft_versions=["1.20.1"],
        ),
        "example.jar",
        BytesIO(b"mod"),
    )
    server = instance_service.create_server(
        CreateServerInstanceRequest(
            id="forge_server",
            display_name="Forge",
            jar_file="server.jar",
            server_type="forge",
            minecraft_version="1.20.1",
        )
    )

    installed = catalog.auto_install_for_server(server)

    assert [item.id for item in installed] == ["example_mod"]
    assert (Path(server.server_dir) / "mods" / "example.jar").read_bytes() == b"mod"


def test_missing_cached_remote_mod_is_downloaded_before_copy(tmp_path: Path, monkeypatch) -> None:
    instance_service, catalog = make_services(tmp_path)
    catalog.add_remote_item(
        ModCatalogItemRequest(
            id="remote_mod",
            display_name="Remote Mod",
            source_type="url",
            source="https://example.test/remote.jar",
            server_types=["paper"],
        )
    )
    monkeypatch.setattr(catalog, "_download_file", lambda url, target: target.write_bytes(b"remote"))
    server = instance_service.create_server(
        CreateServerInstanceRequest(
            id="paper_server",
            display_name="Paper",
            jar_file="server.jar",
            server_type="paper",
            minecraft_version="1.20.1",
        )
    )

    installed = catalog.auto_install_for_server(server)

    assert [item.id for item in installed] == ["remote_mod"]
    assert (Path(server.server_dir) / "plugins" / "remote.jar").read_bytes() == b"remote"
