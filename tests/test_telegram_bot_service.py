from pathlib import Path

import pytest

pytest.importorskip("aiogram")

from app.core.settings import AppSettings
from app.models.settings import TelegramSettings
from app.services.log_buffer import LogBuffer
from app.services.panel_settings import PanelSettingsService
from app.services.telegram_bot import ROLE_ADMIN, ROLE_USER, TelegramBotService


class DummyManager:
    def get_status(self) -> dict[str, str]:
        return {"status": "OFF"}

    def get_work_data(self) -> dict:
        return {"status": "OFF", "active_server": None, "metrics": {}}


def make_service(tmp_path: Path) -> TelegramBotService:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    panel_settings = PanelSettingsService(settings)
    panel_settings.update_telegram_settings(
        TelegramSettings(
            autostart=False,
            bot_token="",
            admin_ids=[1001],
        )
    )
    service = TelegramBotService(panel_settings, DummyManager(), LogBuffer())
    service._admin_ids = {1001}
    return service


def test_telegram_bot_roles_and_blocks_are_persisted(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    assert service._role_for_user_id(1001) == ROLE_ADMIN
    assert service._role_for_user_id(2002) == ROLE_USER

    service._set_user_role(2002, ROLE_ADMIN, username="moderator")
    service._set_user_blocked(2002, True)

    assert service._role_for_user_id(2002) == ROLE_ADMIN
    assert service._is_blocked_user_id(2002) is True


def test_telegram_bot_quick_commands_are_persisted(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    first = service._save_quick_command("Say hi", "say hello")
    second = service._save_quick_command("Say hi", "say hello again")
    updated = service._update_quick_command(first["id"], "say updated")

    assert first["id"] == "say-hi"
    assert second["id"] == "say-hi-2"
    assert updated["command"] == "say updated"
    assert service._delete_quick_command(first["id"]) is True
    assert service._quick_command_by_id(first["id"]) is None


def test_telegram_bot_nickname_validation(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    profile = service._save_nickname(3003, "Steve_123")

    assert profile["minecraft_nickname"] == "Steve_123"
    with pytest.raises(ValueError):
        service._save_nickname(3003, "bad-name!")
