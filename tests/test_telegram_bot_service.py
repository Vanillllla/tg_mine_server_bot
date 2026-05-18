import asyncio
from pathlib import Path

import pytest

pytest.importorskip("aiogram")

from app.core.settings import AppSettings
from app.models.settings import TelegramSettings
from app.services.log_buffer import LogBuffer
from app.services.panel_settings import PanelSettingsService
from app.services.telegram_bot import (
    QUICK_SCOPE_ADMIN_PERSONAL,
    QUICK_SCOPE_USER_SHARED,
    ROLE_ADMIN,
    ROLE_USER,
    TelegramBotService,
)


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

    first = service._save_quick_command("Say hi", "say hello", owner_id=1001)
    second = service._save_quick_command("Say hi", "say hello again", owner_id=1001)
    updated = service._update_quick_command(first["id"], "say updated")

    assert first["id"] == "say-hi"
    assert first["scope"] == QUICK_SCOPE_ADMIN_PERSONAL
    assert first["owner_id"] == 1001
    assert second["id"] == "say-hi-2"
    assert updated["command"] == "say updated"
    assert service._delete_quick_command(first["id"]) is True
    assert service._quick_command_by_id(first["id"]) is None


def test_telegram_bot_quick_commands_are_split_by_audience(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    admin_command = service._save_quick_command("Admin only", "say admin", owner_id=1001)
    service._save_quick_command("Other admin", "say other", owner_id=1002)
    user_command = service._save_quick_command(
        "User command",
        "kill {nick}",
        owner_id=1001,
        scope=QUICK_SCOPE_USER_SHARED,
    )

    assert service._quick_commands_for_role(ROLE_ADMIN, 1001) == [admin_command]
    assert service._quick_commands_for_role(ROLE_USER, 3003) == [user_command]
    assert service._can_use_quick_command(admin_command, ROLE_ADMIN, 1001) is True
    assert service._can_use_quick_command(admin_command, ROLE_ADMIN, 1002) is False
    assert service._can_use_quick_command(user_command, ROLE_USER, 3003) is True
    assert service._can_use_quick_command(user_command, ROLE_ADMIN, 1001) is False


def test_telegram_bot_nickname_validation(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    profile = service._save_nickname(3003, "Steve_123")

    assert profile["minecraft_nickname"] == "Steve_123"
    with pytest.raises(ValueError):
        service._save_nickname(3003, "bad-name!")


def test_telegram_bot_quick_command_substitutes_nickname(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    command = service._save_quick_command(
        "Kill self",
        "kill {nick}",
        owner_id=1001,
        scope=QUICK_SCOPE_USER_SHARED,
    )

    with pytest.raises(ValueError, match="minecraft_nickname_required"):
        service._command_text_for_user(command, 3003)

    service._save_nickname(3003, "Steve_123")

    assert service._command_text_for_user(command, 3003) == "kill Steve_123"


def test_telegram_bot_notification_toggles_are_per_admin(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    assert service._notification_settings(1001)["server_starts"] is False
    assert service._toggle_notification(1001, "server_starts") is True
    assert service._notification_settings(1001)["server_starts"] is True
    assert service._admin_notification_ids("server_starts") == [1001]


def test_telegram_bot_stop_waits_for_dispatcher_polling_shutdown(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    async def scenario() -> None:
        stopped = asyncio.Event()

        class FakeDispatcher:
            stop_called = False

            async def stop_polling(self) -> None:
                self.stop_called = True
                stopped.set()

        async def polling() -> None:
            await stopped.wait()

        dispatcher = FakeDispatcher()
        task = asyncio.create_task(polling())
        service.dispatcher = dispatcher
        service._polling_task = task

        await service.stop()

        assert dispatcher.stop_called is True
        assert task.done() is True
        assert service._polling_task is None
        assert service.dispatcher is None

    asyncio.run(scenario())
