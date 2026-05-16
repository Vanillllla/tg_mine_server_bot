from pathlib import Path

from app.core.json_store import read_json, write_json_atomic
from app.core.settings import AppSettings
from app.models.settings import EmptyShutdownSettings
from app.services.panel_settings import PanelSettingsService


def make_service(tmp_path: Path) -> PanelSettingsService:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    return PanelSettingsService(settings)


def test_public_settings_returns_default_discord_link(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    settings = service.public_settings()

    assert settings.links.discord.url == "https://discord.gg/cUt6nYVEyn"
    assert settings.links.discord.icon_path == "/assets/icons/discord.svg"


def test_public_settings_keeps_custom_discord_link(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    panel = read_json(service.settings.panel_config_path, default={})
    panel["links"] = {
        "discord": {
            "url": "https://discord.gg/custom",
            "icon_path": "/assets/icons/custom.svg",
        },
    }
    write_json_atomic(service.settings.panel_config_path, panel)

    settings = service.public_settings()

    assert settings.links.discord.url == "https://discord.gg/custom"
    assert settings.links.discord.icon_path == "/assets/icons/custom.svg"


def test_empty_shutdown_settings_have_defaults_and_can_be_updated(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    defaults = service.empty_shutdown_settings()
    updated = service.update_empty_shutdown_settings(
        EmptyShutdownSettings(enabled=True, shutdown_if_empty_minutes=12)
    )

    assert defaults.enabled is False
    assert defaults.shutdown_if_empty_minutes == 5
    assert updated.enabled is True
    assert updated.shutdown_if_empty_minutes == 12
