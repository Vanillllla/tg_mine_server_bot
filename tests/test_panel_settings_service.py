from pathlib import Path

from app.core.json_store import read_json, write_json_atomic
from app.core.settings import AppSettings
from app.models.settings import DomainSettings, EmptyShutdownSettings, TelegramSettings
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
    assert settings.domains.minecraft == "mc.vanilla.xazux.ru"
    assert settings.domains.site == ""


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


def test_domain_settings_have_defaults_and_can_be_updated(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    defaults = service.domain_settings()
    updated = service.update_domain_settings(
        DomainSettings(minecraft=" mc.example.ru ", site=" https://panel.example.ru ")
    )
    public = service.public_settings()

    assert defaults.minecraft == "mc.vanilla.xazux.ru"
    assert defaults.site == ""
    assert updated.minecraft == "mc.example.ru"
    assert updated.site == "https://panel.example.ru"
    assert public.domains == updated


def test_telegram_settings_have_defaults_and_can_be_updated(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    defaults = service.telegram_settings()
    updated = service.update_telegram_settings(
        TelegramSettings(
            autostart=True,
            bot_token="123456789:abcdefghijklmnopqrst",
            admin_ids=[1007806948, 1007806948, 123456789],
        )
    )

    assert defaults.autostart is False
    assert defaults.bot_token == ""
    assert defaults.admin_ids == []
    assert updated.autostart is True
    assert updated.bot_token == "123456789:abcdefghijklmnopqrst"
    assert updated.admin_ids == [1007806948, 123456789]
