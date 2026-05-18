import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from app.core.json_store import read_json, write_json_atomic
from app.models.server import ServerStatus
from app.services.log_buffer import LogBuffer
from app.services.minecraft_manager import MinecraftServerManager
from app.services.panel_settings import PanelSettingsService


ROLE_ADMIN = "admin"
ROLE_USER = "user"
QUICK_SCOPE_ADMIN_PERSONAL = "admin_personal"
QUICK_SCOPE_USER_SHARED = "user_shared"

BUTTON_BACK = "⬅️ Назад"
BUTTON_MAIN_MENU = "Главное меню"
BUTTON_QUICK_COMMANDS = "⚡ Быстрые команды"
BUTTON_ONLINE = "Посмотреть онлайн"
BUTTON_HELP = "❓ Помощь"
BUTTON_ADMIN_START = "Запустить сервер"
BUTTON_ADMIN_STOP = "Остановить сервер"
BUTTON_ADMIN_STATUS = "Статус сервера"
BUTTON_ADMIN_SETTINGS = "⚙️ Настройки"
BUTTON_USER_NICKNAME = "Настроить никнейм"
BUTTON_CONSOLE_EXIT = "Выйти из консоли"

LEGACY_BUTTON_STATUS = "Статус"
LEGACY_BUTTON_ONLINE = "Онлайн"
LEGACY_BUTTON_METRICS = "Нагрузка"
LEGACY_BUTTON_CONSOLE = "Консоль"
LEGACY_BUTTON_EXIT = "Выйти из консоли"

NICKNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
USER_ID_RE = re.compile(r"^-?\d+$")
COMMAND_ID_RE = re.compile(r"[^a-z0-9_-]+")

DEFAULT_BOT_DATA: dict[str, Any] = {
    "users": {},
    "quick_commands": [],
    "notifications": {},
}


class TelegramBotStates(StatesGroup):
    console = State()
    quick_command_name = State()
    quick_command_command = State()
    quick_command_edit_command = State()
    add_admin = State()
    remove_admin = State()
    block_user = State()
    unblock_user = State()
    nickname = State()
    user_nickname_identifier = State()
    user_nickname_value = State()
    server_archive = State()


class TelegramBotService:
    def __init__(
        self,
        panel_settings_service: PanelSettingsService,
        manager: MinecraftServerManager,
        log_buffer: LogBuffer,
    ) -> None:
        self.panel_settings_service = panel_settings_service
        self.manager = manager
        self.log_buffer = log_buffer
        self.bot: Bot | None = None
        self.dispatcher: Dispatcher | None = None
        self._polling_task: asyncio.Task | None = None
        self._admin_ids: set[int] = set()
        self._last_error = ""

    @property
    def is_running(self) -> bool:
        return self._polling_task is not None and not self._polling_task.done()

    @property
    def last_error(self) -> str:
        return self._last_error

    async def apply_settings(self, *, raise_errors: bool = False) -> None:
        settings = self.panel_settings_service.telegram_settings()
        self._admin_ids = set(settings.admin_ids)
        if settings.autostart and settings.bot_token:
            try:
                await self.restart()
            except Exception as exc:
                self._last_error = str(exc)
                if raise_errors:
                    raise
            return
        await self.stop()

    async def start(self) -> None:
        if self.is_running:
            return
        settings = self.panel_settings_service.telegram_settings()
        if not settings.bot_token:
            raise RuntimeError("telegram_bot_token_required")

        self._admin_ids = set(settings.admin_ids)
        self._last_error = ""
        self.bot = Bot(token=settings.bot_token)
        self.dispatcher = Dispatcher()
        self._register_handlers(self.dispatcher)
        self._polling_task = asyncio.create_task(self.dispatcher.start_polling(self.bot))
        self._polling_task.add_done_callback(self._capture_polling_error)

    async def restart(self) -> None:
        await self.stop()
        await self.start()

    async def stop(self) -> None:
        task = self._polling_task
        self._polling_task = None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self.bot is not None:
            await self.bot.session.close()
        self.bot = None
        self.dispatcher = None

    def status(self) -> dict[str, Any]:
        settings = self.panel_settings_service.telegram_settings()
        data_admin_ids: set[int] = set()
        for user_id, profile in self._read_bot_data().get("users", {}).items():
            if profile.get("role") != ROLE_ADMIN:
                continue
            try:
                data_admin_ids.add(int(user_id))
            except ValueError:
                continue
        return {
            "running": self.is_running,
            "last_error": self._last_error,
            "configured": bool(settings.bot_token),
            "admin_count": len(set(settings.admin_ids) | data_admin_ids),
        }

    async def notify_server_started_from_web(self, user: Any) -> None:
        role = ROLE_ADMIN if getattr(user, "role", "") == ROLE_ADMIN else ROLE_USER
        await self._notify_server_start(role, "сайта", None)

    def _capture_polling_error(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        try:
            task.result()
        except Exception as exc:
            self._last_error = str(exc)

    def _register_handlers(self, dispatcher: Dispatcher) -> None:
        dispatcher.message.register(self._start, Command("start"))
        dispatcher.callback_query.register(self._handle_callback)
        dispatcher.message.register(self._handle_message)

    def _bot_data_path(self) -> Path:
        return self.panel_settings_service.settings.data_dir / "telegram_bot.json"

    def _read_bot_data(self) -> dict[str, Any]:
        data = read_json(self._bot_data_path(), default={})
        if not isinstance(data, dict):
            data = {}
        changed = False
        for key, default_value in DEFAULT_BOT_DATA.items():
            if key not in data or not isinstance(data[key], type(default_value)):
                if isinstance(default_value, dict):
                    data[key] = default_value.copy()
                else:
                    data[key] = list(default_value)
                changed = True
        if changed:
            self._write_bot_data(data)
        return data

    def _write_bot_data(self, data: dict[str, Any]) -> None:
        write_json_atomic(self._bot_data_path(), data)

    def _role_for_user_id(self, user_id: int) -> str:
        if user_id in self._admin_ids:
            return ROLE_ADMIN
        profile = self._read_bot_data().get("users", {}).get(str(user_id), {})
        return ROLE_ADMIN if profile.get("role") == ROLE_ADMIN else ROLE_USER

    def _is_blocked_user_id(self, user_id: int) -> bool:
        profile = self._read_bot_data().get("users", {}).get(str(user_id), {})
        return bool(profile.get("is_blocked", False))

    def _ensure_user_profile(self, telegram_user: Any) -> dict[str, Any]:
        data = self._read_bot_data()
        users = data.setdefault("users", {})
        user_id = int(telegram_user.id)
        key = str(user_id)
        existing = users.get(key, {})
        role = (
            ROLE_ADMIN
            if user_id in self._admin_ids or existing.get("role") == ROLE_ADMIN
            else ROLE_USER
        )
        profile = {
            "telegram_id": user_id,
            "username": getattr(telegram_user, "username", None),
            "role": role,
            "is_blocked": bool(existing.get("is_blocked", False)),
            "minecraft_nickname": existing.get("minecraft_nickname"),
        }
        if existing != profile:
            users[key] = profile
            self._write_bot_data(data)
        return profile

    def _set_user_role(
        self,
        user_id: int,
        role: str,
        username: str | None = None,
    ) -> dict[str, Any]:
        data = self._read_bot_data()
        users = data.setdefault("users", {})
        existing = users.get(str(user_id), {})
        profile = {
            "telegram_id": user_id,
            "username": username if username is not None else existing.get("username"),
            "role": role,
            "is_blocked": bool(existing.get("is_blocked", False)),
            "minecraft_nickname": existing.get("minecraft_nickname"),
        }
        users[str(user_id)] = profile
        self._write_bot_data(data)
        return profile

    def _set_user_blocked(self, user_id: int, blocked: bool) -> dict[str, Any]:
        data = self._read_bot_data()
        users = data.setdefault("users", {})
        existing = users.get(str(user_id), {})
        role = existing.get("role") or (ROLE_ADMIN if user_id in self._admin_ids else ROLE_USER)
        profile = {
            "telegram_id": user_id,
            "username": existing.get("username"),
            "role": role,
            "is_blocked": blocked,
            "minecraft_nickname": existing.get("minecraft_nickname"),
        }
        users[str(user_id)] = profile
        self._write_bot_data(data)
        return profile

    def _save_nickname(self, user_id: int, nickname: str) -> dict[str, Any]:
        nickname = self._normalize_nickname(nickname)
        data = self._read_bot_data()
        users = data.setdefault("users", {})
        existing = users.get(str(user_id), {})
        role = existing.get("role") or (ROLE_ADMIN if user_id in self._admin_ids else ROLE_USER)
        profile = {
            "telegram_id": user_id,
            "username": existing.get("username"),
            "role": role,
            "is_blocked": bool(existing.get("is_blocked", False)),
            "minecraft_nickname": nickname,
        }
        users[str(user_id)] = profile
        self._write_bot_data(data)
        return profile

    @staticmethod
    def _normalize_nickname(value: str) -> str:
        nickname = value.strip()
        if not NICKNAME_RE.match(nickname):
            raise ValueError("minecraft_nickname_invalid")
        return nickname

    def _quick_commands(self) -> list[dict[str, Any]]:
        commands = self._read_bot_data().setdefault("quick_commands", [])
        return [command for command in commands if isinstance(command, dict)]

    def _quick_commands_for_role(self, role: str, user_id: int | None) -> list[dict[str, Any]]:
        commands = self._quick_commands()
        if role == ROLE_ADMIN:
            return [
                command
                for command in commands
                if command.get("scope", QUICK_SCOPE_ADMIN_PERSONAL) == QUICK_SCOPE_ADMIN_PERSONAL
                and int(command.get("owner_id") or 0) == int(user_id or 0)
            ]
        return [
            command
            for command in commands
            if command.get("scope", QUICK_SCOPE_ADMIN_PERSONAL) == QUICK_SCOPE_USER_SHARED
        ]

    def _user_shared_quick_commands(self) -> list[dict[str, Any]]:
        return [
            command
            for command in self._quick_commands()
            if command.get("scope", QUICK_SCOPE_ADMIN_PERSONAL) == QUICK_SCOPE_USER_SHARED
        ]

    def _quick_command_by_id(self, command_id: str) -> dict[str, Any] | None:
        return next(
            (command for command in self._quick_commands() if command.get("id") == command_id),
            None,
        )

    def _save_quick_command(
        self,
        title: str,
        command: str,
        *,
        owner_id: int | None = None,
        scope: str = QUICK_SCOPE_ADMIN_PERSONAL,
    ) -> dict[str, Any]:
        title = title.strip()
        command = command.strip()
        if not title:
            raise ValueError("quick_command_title_required")
        if not command:
            raise ValueError("quick_command_command_required")
        if scope not in {QUICK_SCOPE_ADMIN_PERSONAL, QUICK_SCOPE_USER_SHARED}:
            raise ValueError("quick_command_scope_invalid")
        if scope == QUICK_SCOPE_ADMIN_PERSONAL and not owner_id:
            raise ValueError("quick_command_owner_required")

        data = self._read_bot_data()
        commands = data.setdefault("quick_commands", [])
        existing_ids = {str(item.get("id", "")) for item in commands if isinstance(item, dict)}
        command_id = self._make_command_id(title, existing_ids)
        payload = {
            "id": command_id,
            "title": title,
            "command": command,
            "owner_id": owner_id,
            "scope": scope,
            "visible_for_roles": [ROLE_USER] if scope == QUICK_SCOPE_USER_SHARED else [ROLE_ADMIN],
            "require_server_online": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        commands.append(payload)
        self._write_bot_data(data)
        return payload

    def _update_quick_command(self, command_id: str, command_text: str) -> dict[str, Any]:
        command_text = command_text.strip()
        if not command_text:
            raise ValueError("quick_command_command_required")
        data = self._read_bot_data()
        commands = data.setdefault("quick_commands", [])
        for command in commands:
            if command.get("id") == command_id:
                command["command"] = command_text
                command["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write_bot_data(data)
                return command
        raise KeyError(command_id)

    def _delete_quick_command(self, command_id: str) -> bool:
        data = self._read_bot_data()
        commands = data.setdefault("quick_commands", [])
        next_commands = [item for item in commands if item.get("id") != command_id]
        if len(next_commands) == len(commands):
            return False
        data["quick_commands"] = next_commands
        self._write_bot_data(data)
        return True

    @staticmethod
    def _make_command_id(title: str, existing_ids: set[str]) -> str:
        candidate = COMMAND_ID_RE.sub("-", title.lower()).strip("-_")[:32] or "command"
        command_id = candidate
        suffix = 2
        while command_id in existing_ids:
            tail = f"-{suffix}"
            command_id = f"{candidate[: 32 - len(tail)]}{tail}"
            suffix += 1
        return command_id

    def _main_keyboard(self, role: str) -> ReplyKeyboardMarkup:
        if role == ROLE_ADMIN:
            toggle_button = BUTTON_ADMIN_STOP if self._server_is_online() else BUTTON_ADMIN_START
            keyboard = [
                [KeyboardButton(text=toggle_button)],
                [KeyboardButton(text=BUTTON_QUICK_COMMANDS), KeyboardButton(text=BUTTON_ONLINE)],
                [
                    KeyboardButton(text=BUTTON_ADMIN_STATUS),
                    KeyboardButton(text=BUTTON_ADMIN_SETTINGS),
                ],
            ]
        else:
            keyboard = [
                [KeyboardButton(text=BUTTON_ADMIN_START)],
                [KeyboardButton(text=BUTTON_ONLINE), KeyboardButton(text=BUTTON_QUICK_COMMANDS)],
                [KeyboardButton(text=BUTTON_HELP), KeyboardButton(text=BUTTON_USER_NICKNAME)],
            ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    @staticmethod
    def _console_keyboard() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=BUTTON_BACK), KeyboardButton(text=BUTTON_CONSOLE_EXIT)]],
            resize_keyboard=True,
        )

    @staticmethod
    def _inline_keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=text, callback_data=callback_data)
                    for text, callback_data in row
                ]
                for row in rows
            ]
        )

    def _notification_settings(self, user_id: int | None) -> dict[str, bool]:
        if not user_id:
            return {"system_restarts": False, "server_starts": False}
        notifications = self._read_bot_data().setdefault("notifications", {})
        settings = notifications.get(str(user_id), {})
        return {
            "system_restarts": bool(settings.get("system_restarts", False)),
            "server_starts": bool(settings.get("server_starts", False)),
        }

    def _toggle_notification(self, user_id: int, key: str) -> bool:
        if key not in {"system_restarts", "server_starts"}:
            raise KeyError(key)
        data = self._read_bot_data()
        notifications = data.setdefault("notifications", {})
        settings = notifications.setdefault(str(user_id), {})
        settings[key] = not bool(settings.get(key, False))
        self._write_bot_data(data)
        return bool(settings[key])

    def _notifications_screen(self, user_id: int | None) -> tuple[str, InlineKeyboardMarkup]:
        settings = self._notification_settings(user_id)
        system_state = "ON" if settings["system_restarts"] else "OFF"
        server_state = "ON" if settings["server_starts"] else "OFF"
        return (
            "Настройка уведомлений",
            self._inline_keyboard(
                [
                    [
                        (
                            f"Перезапуск бота/сайта/системы: {system_state}",
                            "toggle_notify:system_restarts",
                        )
                    ],
                    [(f"Включение сервера: {server_state}", "toggle_notify:server_starts")],
                    [(BUTTON_BACK, "nav:back")],
                ]
            ),
        )

    def _admin_notification_ids(self, key: str) -> list[int]:
        data = self._read_bot_data()
        users = data.get("users", {})
        notifications = data.get("notifications", {})
        result: list[int] = []
        for user_id, settings in notifications.items():
            try:
                telegram_id = int(user_id)
            except ValueError:
                continue
            if not settings.get(key):
                continue
            profile = users.get(user_id, {})
            if telegram_id in self._admin_ids or profile.get("role") == ROLE_ADMIN:
                result.append(telegram_id)
        return result

    async def _notify_admins(self, key: str, text: str) -> None:
        if self.bot is None:
            return
        for user_id in self._admin_notification_ids(key):
            try:
                await self.bot.send_message(user_id, text)
            except Exception as exc:
                self._last_error = str(exc)

    async def _notify_system_event(self, text: str) -> None:
        await self._notify_admins("system_restarts", text)

    async def _notify_server_start(self, role: str, source: str, actor_id: int | None) -> None:
        actor = "админ" if role == ROLE_ADMIN else "простой пользователь"
        actor_id_text = f" Telegram ID: {actor_id}" if actor_id else ""
        await self._notify_admins(
            "server_starts",
            f"Сервер включён.\nИсточник: {actor} с {source}.{actor_id_text}",
        )

    def _quick_commands_keyboard(self, role: str, user_id: int | None) -> InlineKeyboardMarkup:
        rows = [
            [(str(command.get("title") or command.get("id")), f"quick:{command.get('id')}")]
            for command in self._quick_commands_for_role(role, user_id)
        ]
        if role == ROLE_ADMIN:
            rows.append([("➕ Добавить команду себе", "fsm:quick_command.wait_name")])
            rows.append([("⚙️ Команды пользователей", "nav:admin.quick_command_settings")])
        rows.append([(BUTTON_BACK, "nav:back")])
        return self._inline_keyboard(rows)

    def _screen_payload(
        self,
        screen_id: str,
        role: str,
        user_id: int | None = None,
    ) -> tuple[str, InlineKeyboardMarkup]:
        if screen_id == "common.quick_commands":
            return (
                "Быстрые команды\nВыберите команду:",
                self._quick_commands_keyboard(role, user_id),
            )
        if screen_id == "common.help":
            return self._help_text(role), self._inline_keyboard([[(BUTTON_BACK, "nav:back")]])
        if screen_id == "admin.settings.page_1" and role == ROLE_ADMIN:
            return (
                "Панель настроек — меню 1",
                self._inline_keyboard(
                    [
                        [
                            ("⌨️ Консоль сервера", "fsm:admin.console_mode"),
                            ("Пользователи", "nav:admin.users"),
                        ],
                        [
                            ("Настройка никнейма пользователя", "nav:admin.user_nickname_settings"),
                            ("Настройка уведомлений", "nav:admin.notifications"),
                        ],
                        [("➡️ Ещё настройки", "nav:admin.settings.page_2")],
                        [(BUTTON_BACK, "nav:back")],
                    ]
                ),
            )
        if screen_id == "admin.settings.page_2" and role == ROLE_ADMIN:
            return (
                "Панель настроек — меню 2",
                self._inline_keyboard(
                    [
                        [
                            ("❓ Помощь", "nav:common.help"),
                            ("Перезапустить бота", "confirm:bot.restart"),
                        ],
                        [
                            ("Настройки бот-панели", "nav:admin.bot_panel_settings"),
                            ("Настройки пользователя", "nav:admin.user_settings"),
                        ],
                        [(BUTTON_BACK, "nav:back")],
                    ]
                ),
            )
        if screen_id == "admin.users" and role == ROLE_ADMIN:
            return (
                "Панель пользователей",
                self._inline_keyboard(
                    [
                        [
                            ("➕ Добавить администратора", "fsm:users.wait_add_admin_id"),
                            ("➖ Удалить администратора", "fsm:users.wait_remove_admin_id"),
                        ],
                        [
                            ("Заблокировать пользователя", "fsm:users.wait_block_user_id"),
                            ("✅ Разблокировать пользователя", "fsm:users.wait_unblock_user_id"),
                        ],
                        [(BUTTON_BACK, "nav:back")],
                    ]
                ),
            )
        if screen_id == "admin.quick_command_settings" and role == ROLE_ADMIN:
            return (
                "Настройка быстрых команд пользователей",
                self._inline_keyboard(
                    [
                        [
                            (
                                "➕ Добавить команду пользователям",
                                "fsm:quick_command.wait_public_name",
                            )
                        ],
                        [("✏️ Изменить команду", "menu:quick_edit")],
                        [("Удалить команду", "menu:quick_delete")],
                        [(BUTTON_BACK, "nav:back")],
                    ]
                ),
            )
        if screen_id == "admin.user_nickname_settings" and role == ROLE_ADMIN:
            return (
                "Настройка никнейма пользователя",
                self._inline_keyboard(
                    [
                        [("✏️ Установить ник по Telegram ID", "fsm:users.wait_nickname_user_id")],
                        [(BUTTON_BACK, "nav:back")],
                    ]
                ),
            )
        if screen_id == "admin.notifications" and role == ROLE_ADMIN:
            return self._notifications_screen(user_id)
        if screen_id == "user.nickname_settings":
            return (
                "Настройка никнейма\nВведите ваш никнейм в Minecraft.",
                self._inline_keyboard(
                    [
                        [("✏️ Ввести ник", "fsm:nickname.wait_value")],
                        [(BUTTON_BACK, "nav:back")],
                    ]
                ),
            )
        if screen_id == "admin.bot_panel_settings" and role == ROLE_ADMIN:
            return (
                "Настройки бот-панели\n"
                "Токен, автозапуск и список базовых админов редактируются в web-панели.",
                self._inline_keyboard([[(BUTTON_BACK, "nav:back")]]),
            )
        if screen_id == "admin.user_settings" and role == ROLE_ADMIN:
            return (
                "Настройки пользователя\n"
                "Доступные действия вынесены в панель пользователей.",
                self._inline_keyboard([[(BUTTON_BACK, "nav:back")]]),
            )
        return (
            "Раздел недоступен для вашей роли.",
            self._inline_keyboard([[(BUTTON_BACK, "nav:back")]]),
        )

    @staticmethod
    def _help_text(role: str) -> str:
        base = [
            "Помощь",
            "• Запуск сервера доступен из главного меню.",
            "• Онлайн показывает ответ команды list.",
            "• Быстрые команды выполняют заранее сохранённые console-команды.",
        ]
        if role == ROLE_ADMIN:
            base.extend(
                [
                    "• Админ может останавливать сервер и открывать консоль.",
                    "• Управление пользователями и быстрыми командами находится в настройках.",
                ]
            )
        return "\n".join(base)

    async def _start(self, message: Message, state: FSMContext) -> None:
        profile = await self._profile_from_message(message)
        if profile is None:
            return
        await state.clear()
        await state.update_data(current_screen=f"{profile['role']}.main", nav_stack=[])
        await message.answer(
            self._main_title(profile["role"]),
            reply_markup=self._main_keyboard(profile["role"]),
        )

    async def _handle_message(self, message: Message, state: FSMContext) -> None:
        profile = await self._profile_from_message(message)
        if profile is None:
            return

        text = (message.text or "").strip()
        current_state = await state.get_state()
        if current_state:
            await self._handle_state_message(message, state, profile, current_state, text)
            return

        role = profile["role"]
        if text == BUTTON_ADMIN_START:
            await self._start_server(message, role)
        elif text == BUTTON_ADMIN_STOP and role == ROLE_ADMIN:
            await self._stop_server(message)
        elif (
            text in {BUTTON_ADMIN_STATUS, LEGACY_BUTTON_STATUS, LEGACY_BUTTON_METRICS}
            and role == ROLE_ADMIN
        ):
            await message.answer(self._status_text(), reply_markup=self._main_keyboard(role))
        elif text in {BUTTON_ONLINE, LEGACY_BUTTON_ONLINE}:
            await self._send_online(message)
        elif text == BUTTON_QUICK_COMMANDS:
            await self._open_screen(message, state, "common.quick_commands", role)
        elif text == BUTTON_HELP:
            await self._open_screen(message, state, "common.help", role)
        elif text == BUTTON_USER_NICKNAME:
            await self._open_screen(message, state, "user.nickname_settings", role)
        elif text == BUTTON_ADMIN_SETTINGS and role == ROLE_ADMIN:
            await self._open_screen(message, state, "admin.settings.page_1", role)
        elif text == LEGACY_BUTTON_CONSOLE and role == ROLE_ADMIN:
            await self._start_fsm(message, state, "admin.console_mode", role)
        else:
            await message.answer("Неизвестная команда.", reply_markup=self._main_keyboard(role))

    async def _handle_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        message = callback.message
        if callback.from_user is None:
            await callback.answer("Пользователь не найден.", show_alert=True)
            return
        profile = self._ensure_user_profile(callback.from_user)
        if profile.get("is_blocked"):
            await callback.answer("Вы заблокированы.", show_alert=True)
            return

        role = profile["role"]
        data = callback.data or ""
        if data == "nav:back":
            await self._go_back(callback, state, role)
        elif data.startswith("nav:"):
            await self._open_screen(callback, state, data.removeprefix("nav:"), role)
        elif data.startswith("fsm:"):
            if message is not None:
                await self._start_fsm(message, state, data.removeprefix("fsm:"), role)
            await callback.answer()
        elif data.startswith("quick:"):
            await self._execute_quick_command(callback, data.removeprefix("quick:"), role)
        elif data == "menu:quick_edit":
            await self._show_quick_command_picker(callback, "edit", role)
        elif data == "menu:quick_delete":
            await self._show_quick_command_picker(callback, "delete", role)
        elif data.startswith("quick_edit:"):
            await self._start_edit_quick_command(
                callback,
                state,
                data.removeprefix("quick_edit:"),
                role,
            )
        elif data.startswith("quick_delete:"):
            await self._delete_quick_command_callback(
                callback,
                data.removeprefix("quick_delete:"),
                role,
            )
        elif data == "confirm:bot.restart":
            await self._confirm_restart(callback, role)
        elif data == "action:bot.restart":
            await self._restart_from_callback(callback, role)
        elif data.startswith("toggle_notify:"):
            await self._toggle_notification_callback(
                callback,
                data.removeprefix("toggle_notify:"),
                role,
            )
        else:
            await callback.answer("Действие не найдено.", show_alert=True)

    async def _profile_from_message(self, message: Message) -> dict[str, Any] | None:
        if message.from_user is None:
            return None
        profile = self._ensure_user_profile(message.from_user)
        if profile.get("is_blocked"):
            await message.answer("Вы заблокированы.")
            return None
        return profile

    async def _open_screen(
        self,
        source: Message | CallbackQuery,
        state: FSMContext,
        screen_id: str,
        role: str,
    ) -> None:
        if role != ROLE_ADMIN and screen_id.startswith("admin."):
            await self._send_response(source, "Раздел доступен только администратору.")
            return

        data = await state.get_data()
        current = data.get("current_screen")
        stack = list(data.get("nav_stack", []))
        if current and current != screen_id:
            stack.append(current)
        await state.update_data(current_screen=screen_id, nav_stack=stack[-10:])

        if screen_id in {"admin.main", "user.main"}:
            await self._send_response(
                source,
                self._main_title(role),
                reply_markup=self._main_keyboard(role),
            )
            return

        text, markup = self._screen_payload(screen_id, role, self._source_user_id(source))
        await self._send_response(source, text, reply_markup=markup, edit_inline=True)

    async def _go_back(self, callback: CallbackQuery, state: FSMContext, role: str) -> None:
        current_state = await state.get_state()
        if current_state:
            await state.clear()
            await state.update_data(current_screen=f"{role}.main", nav_stack=[])
            await self._send_response(
                callback,
                self._main_title(role),
                reply_markup=self._main_keyboard(role),
            )
            await callback.answer()
            return

        data = await state.get_data()
        stack = list(data.get("nav_stack", []))
        screen_id = stack.pop() if stack else f"{role}.main"
        await state.update_data(current_screen=screen_id, nav_stack=stack)
        if screen_id in {"admin.main", "user.main"}:
            await self._send_response(
                callback,
                self._main_title(role),
                reply_markup=self._main_keyboard(role),
            )
        else:
            text, markup = self._screen_payload(screen_id, role, callback.from_user.id)
            await self._send_response(callback, text, reply_markup=markup, edit_inline=True)
        await callback.answer()

    @staticmethod
    def _source_user_id(source: Message | CallbackQuery) -> int | None:
        user = source.from_user
        return int(user.id) if user is not None else None

    async def _send_response(
        self,
        source: Message | CallbackQuery,
        text: str,
        *,
        reply_markup: ReplyKeyboardMarkup | InlineKeyboardMarkup | None = None,
        edit_inline: bool = False,
    ) -> None:
        if isinstance(source, Message):
            await source.answer(text, reply_markup=reply_markup)
            return

        if edit_inline and source.message is not None:
            try:
                await source.message.edit_text(text, reply_markup=reply_markup)
                await source.answer()
                return
            except Exception:
                pass
        if source.message is not None:
            await source.message.answer(text, reply_markup=reply_markup)
        await source.answer()

    async def _start_fsm(
        self,
        message: Message,
        state: FSMContext,
        state_id: str,
        role: str,
    ) -> None:
        if role != ROLE_ADMIN and not state_id.startswith("nickname."):
            await message.answer("Действие доступно только администратору.")
            return

        prompts = {
            "admin.console_mode": (
                "Режим консоли. Отправьте команду серверу.",
                TelegramBotStates.console,
            ),
            "quick_command.wait_name": (
                "Введите название личной быстрой команды.",
                TelegramBotStates.quick_command_name,
            ),
            "quick_command.wait_public_name": (
                "Введите название быстрой команды для простых пользователей.",
                TelegramBotStates.quick_command_name,
            ),
            "users.wait_add_admin_id": (
                "Введите Telegram ID пользователя или @username, "
                "если пользователь уже писал боту.",
                TelegramBotStates.add_admin,
            ),
            "users.wait_remove_admin_id": (
                "Введите Telegram ID администратора или @username.",
                TelegramBotStates.remove_admin,
            ),
            "users.wait_block_user_id": (
                "Введите Telegram ID пользователя или @username.",
                TelegramBotStates.block_user,
            ),
            "users.wait_unblock_user_id": (
                "Введите Telegram ID пользователя или @username.",
                TelegramBotStates.unblock_user,
            ),
            "nickname.wait_value": ("Введите ваш Minecraft-ник.", TelegramBotStates.nickname),
            "users.wait_nickname_user_id": (
                "Введите Telegram ID пользователя или @username.",
                TelegramBotStates.user_nickname_identifier,
            ),
        }
        if state_id == "files.wait_server_archive":
            await message.answer(
                "Загрузка серверного архива через Telegram пока не подключена к backend. "
                "Используйте web-панель."
            )
            return
        prompt = prompts.get(state_id)
        if prompt is None:
            await message.answer("Состояние не найдено.")
            return

        await state.set_state(prompt[1])
        data: dict[str, Any] = {"return_screen": await self._current_screen(state, role)}
        if state_id == "quick_command.wait_name" and message.from_user is not None:
            data["quick_command_scope"] = QUICK_SCOPE_ADMIN_PERSONAL
            data["quick_command_owner_id"] = message.from_user.id
        if state_id == "quick_command.wait_public_name":
            data["quick_command_scope"] = QUICK_SCOPE_USER_SHARED
            data["quick_command_owner_id"] = message.from_user.id if message.from_user else None
        await state.update_data(**data)
        reply_markup = self._console_keyboard() if prompt[1] == TelegramBotStates.console else None
        await message.answer(prompt[0], reply_markup=reply_markup)

    async def _handle_state_message(
        self,
        message: Message,
        state: FSMContext,
        profile: dict[str, Any],
        current_state: str,
        text: str,
    ) -> None:
        role = profile["role"]
        if text in {BUTTON_BACK, BUTTON_MAIN_MENU, BUTTON_CONSOLE_EXIT, LEGACY_BUTTON_EXIT}:
            await state.clear()
            await state.update_data(current_screen=f"{role}.main", nav_stack=[])
            await message.answer(self._main_title(role), reply_markup=self._main_keyboard(role))
            return

        if current_state == TelegramBotStates.console.state:
            await self._send_console_command(message, text)
            return
        if current_state == TelegramBotStates.quick_command_name.state:
            if not text:
                await message.answer("Название команды не задано.")
                return
            await state.update_data(quick_command_title=text)
            await state.set_state(TelegramBotStates.quick_command_command)
            await message.answer("Введите команду, которая будет отправляться на сервер.")
            return
        if current_state == TelegramBotStates.quick_command_command.state:
            await self._finish_add_quick_command(message, state, text, role)
            return
        if current_state == TelegramBotStates.quick_command_edit_command.state:
            await self._finish_edit_quick_command(message, state, text, role)
            return
        if current_state == TelegramBotStates.add_admin.state:
            await self._finish_user_role_update(message, state, text, role, ROLE_ADMIN)
            return
        if current_state == TelegramBotStates.remove_admin.state:
            await self._finish_user_role_update(message, state, text, role, ROLE_USER)
            return
        if current_state == TelegramBotStates.block_user.state:
            await self._finish_user_block_update(message, state, text, role, True)
            return
        if current_state == TelegramBotStates.unblock_user.state:
            await self._finish_user_block_update(message, state, text, role, False)
            return
        if current_state == TelegramBotStates.nickname.state:
            await self._finish_nickname(message, state, text, role)
            return
        if current_state == TelegramBotStates.user_nickname_identifier.state:
            await self._handle_user_nickname_identifier(message, state, text)
            return
        if current_state == TelegramBotStates.user_nickname_value.state:
            await self._finish_user_nickname(message, state, text, role)
            return
        if current_state == TelegramBotStates.server_archive.state:
            await message.answer("Загрузка архива через Telegram пока не реализована.")

    async def _finish_add_quick_command(
        self,
        message: Message,
        state: FSMContext,
        command_text: str,
        role: str,
    ) -> None:
        data = await state.get_data()
        title = str(data.get("quick_command_title", ""))
        try:
            self._save_quick_command(
                title,
                command_text,
                owner_id=data.get("quick_command_owner_id"),
                scope=str(data.get("quick_command_scope") or QUICK_SCOPE_ADMIN_PERSONAL),
            )
        except ValueError as exc:
            await message.answer(f"Команда не сохранена: {exc}")
            return
        await state.clear()
        return_screen = (
            "admin.quick_command_settings"
            if data.get("quick_command_scope") == QUICK_SCOPE_USER_SHARED
            else "common.quick_commands"
        )
        await state.update_data(current_screen=return_screen, nav_stack=[])
        await message.answer("Быстрая команда сохранена.")
        await self._open_screen(message, state, return_screen, role)

    async def _finish_edit_quick_command(
        self,
        message: Message,
        state: FSMContext,
        command_text: str,
        role: str,
    ) -> None:
        data = await state.get_data()
        command_id = str(data.get("edit_command_id", ""))
        try:
            self._update_quick_command(command_id, command_text)
        except (KeyError, ValueError) as exc:
            await message.answer(f"Команда не изменена: {exc}")
            return
        await state.clear()
        await state.update_data(current_screen="admin.quick_command_settings", nav_stack=[])
        await message.answer("Быстрая команда изменена.")
        await self._open_screen(message, state, "admin.quick_command_settings", role)

    async def _finish_user_role_update(
        self,
        message: Message,
        state: FSMContext,
        identifier: str,
        role: str,
        target_role: str,
    ) -> None:
        user_id = self._resolve_user_identifier(identifier)
        if user_id is None:
            await message.answer(
                "Пользователь не найден. Укажите Telegram ID или уже известный @username."
            )
            return
        if message.from_user and user_id == message.from_user.id and target_role != ROLE_ADMIN:
            await message.answer("Нельзя снять права администратора с самого себя.")
            return
        if target_role == ROLE_USER and user_id in self._admin_ids:
            await message.answer(
                "Этот администратор задан в web-настройках Telegram "
                "и не может быть снят через бота."
            )
            return
        self._set_user_role(user_id, target_role)
        await state.clear()
        await state.update_data(current_screen="admin.users", nav_stack=[])
        await message.answer("Права пользователя обновлены.")
        await self._open_screen(message, state, "admin.users", role)

    async def _finish_user_block_update(
        self,
        message: Message,
        state: FSMContext,
        identifier: str,
        role: str,
        blocked: bool,
    ) -> None:
        user_id = self._resolve_user_identifier(identifier)
        if user_id is None:
            await message.answer(
                "Пользователь не найден. Укажите Telegram ID или уже известный @username."
            )
            return
        if message.from_user and user_id == message.from_user.id and blocked:
            await message.answer("Нельзя заблокировать самого себя.")
            return
        if blocked and user_id in self._admin_ids:
            await message.answer("Нельзя заблокировать администратора из web-настроек Telegram.")
            return
        self._set_user_blocked(user_id, blocked)
        await state.clear()
        await state.update_data(current_screen="admin.users", nav_stack=[])
        await message.answer("Блокировка пользователя обновлена.")
        await self._open_screen(message, state, "admin.users", role)

    async def _finish_nickname(
        self,
        message: Message,
        state: FSMContext,
        nickname: str,
        role: str,
    ) -> None:
        if message.from_user is None:
            return
        try:
            self._save_nickname(message.from_user.id, nickname)
        except ValueError:
            await message.answer("Ник должен быть 3-16 символов: латиница, цифры или _.")
            return
        await state.clear()
        await state.update_data(current_screen=f"{role}.main", nav_stack=[])
        await message.answer("Никнейм сохранён.", reply_markup=self._main_keyboard(role))

    async def _handle_user_nickname_identifier(
        self,
        message: Message,
        state: FSMContext,
        identifier: str,
    ) -> None:
        user_id = self._resolve_user_identifier(identifier)
        if user_id is None:
            await message.answer(
                "Пользователь не найден. Укажите Telegram ID или известный @username."
            )
            return
        await state.update_data(target_nickname_user_id=user_id)
        await state.set_state(TelegramBotStates.user_nickname_value)
        await message.answer("Введите Minecraft-ник для этого пользователя.")

    async def _finish_user_nickname(
        self,
        message: Message,
        state: FSMContext,
        nickname: str,
        role: str,
    ) -> None:
        data = await state.get_data()
        user_id = int(data.get("target_nickname_user_id") or 0)
        if not user_id:
            await message.answer("Пользователь для настройки ника не выбран.")
            return
        try:
            self._save_nickname(user_id, nickname)
        except ValueError:
            await message.answer("Ник должен быть 3-16 символов: латиница, цифры или _.")
            return
        await state.clear()
        await state.update_data(current_screen="admin.user_nickname_settings", nav_stack=[])
        await message.answer("Никнейм пользователя сохранён.")
        await self._open_screen(message, state, "admin.user_nickname_settings", role)

    def _resolve_user_identifier(self, identifier: str) -> int | None:
        normalized = identifier.strip()
        if USER_ID_RE.match(normalized):
            user_id = int(normalized)
            return user_id if user_id > 0 else None
        username = normalized.removeprefix("@").lower()
        if not username:
            return None
        for key, profile in self._read_bot_data().get("users", {}).items():
            if str(profile.get("username", "")).lower() == username:
                return int(key)
        return None

    async def _current_screen(self, state: FSMContext, role: str) -> str:
        data = await state.get_data()
        return str(data.get("current_screen") or f"{role}.main")

    @staticmethod
    def _can_use_quick_command(command: dict[str, Any], role: str, user_id: int) -> bool:
        scope = command.get("scope", QUICK_SCOPE_ADMIN_PERSONAL)
        if scope == QUICK_SCOPE_ADMIN_PERSONAL:
            return role == ROLE_ADMIN and int(command.get("owner_id") or 0) == user_id
        if scope == QUICK_SCOPE_USER_SHARED:
            return role == ROLE_USER
        return False

    def _command_text_for_user(self, command: dict[str, Any], user_id: int) -> str:
        command_text = str(command.get("command", "")).strip()
        if not command_text:
            raise ValueError("quick_command_command_required")
        if "{nick}" not in command_text:
            return command_text
        nickname = (
            self._read_bot_data()
            .get("users", {})
            .get(str(user_id), {})
            .get("minecraft_nickname")
        )
        if not nickname:
            raise ValueError("minecraft_nickname_required")
        return command_text.replace("{nick}", str(nickname))

    async def _execute_quick_command(
        self,
        callback: CallbackQuery,
        command_id: str,
        role: str,
    ) -> None:
        command = self._quick_command_by_id(command_id)
        if command is None:
            await callback.answer("Команда не найдена.", show_alert=True)
            return
        if not self._can_use_quick_command(command, role, callback.from_user.id):
            await callback.answer(
                "Команда недоступна для вашей роли.",
                show_alert=True,
            )
            return
        try:
            command_text = self._command_text_for_user(command, callback.from_user.id)
        except ValueError as exc:
            if str(exc) == "minecraft_nickname_required":
                await callback.answer(
                    "Сначала настройте Minecraft-ник.",
                    show_alert=True,
                )
                return
            await callback.answer("Команда пустая.", show_alert=True)
            return
        if not command_text:
            await callback.answer("Команда пустая.", show_alert=True)
            return
        try:
            await self.manager.send_stdin_command(command_text)
        except RuntimeError as exc:
            await callback.answer(
                f"Команда не отправлена: {exc}",
                show_alert=True,
            )
            return
        await callback.answer("Команда отправлена.")

    async def _show_quick_command_picker(
        self,
        callback: CallbackQuery,
        mode: str,
        role: str,
    ) -> None:
        if role != ROLE_ADMIN:
            await callback.answer("Только для администратора.", show_alert=True)
            return
        commands = self._user_shared_quick_commands()
        if not commands:
            await callback.answer("Команды пользователей не настроены.", show_alert=True)
            return
        prefix = "quick_edit" if mode == "edit" else "quick_delete"
        rows = [
            [(str(command.get("title") or command.get("id")), f"{prefix}:{command.get('id')}")]
            for command in commands
        ]
        rows.append([(BUTTON_BACK, "nav:back")])
        await self._send_response(
            callback,
            "Выберите быструю команду:",
            reply_markup=self._inline_keyboard(rows),
            edit_inline=True,
        )

    async def _start_edit_quick_command(
        self,
        callback: CallbackQuery,
        state: FSMContext,
        command_id: str,
        role: str,
    ) -> None:
        if role != ROLE_ADMIN or callback.message is None:
            await callback.answer("Только для администратора.", show_alert=True)
            return
        command = self._quick_command_by_id(command_id)
        if command is None:
            await callback.answer("Команда не найдена.", show_alert=True)
            return
        await state.set_state(TelegramBotStates.quick_command_edit_command)
        await state.update_data(
            edit_command_id=command_id,
            current_screen="admin.quick_command_settings",
        )
        await callback.message.answer(
            f"Введите новую команду для «{command.get('title')}».\n"
            f"Текущая: {command.get('command')}"
        )
        await callback.answer()

    async def _delete_quick_command_callback(
        self,
        callback: CallbackQuery,
        command_id: str,
        role: str,
    ) -> None:
        if role != ROLE_ADMIN:
            await callback.answer("Только для администратора.", show_alert=True)
            return
        deleted = self._delete_quick_command(command_id)
        if not deleted:
            await callback.answer("Команда не найдена.", show_alert=True)
            return
        await self._send_response(
            callback,
            "Быстрая команда удалена.",
            reply_markup=self._screen_payload(
                "admin.quick_command_settings",
                role,
                callback.from_user.id,
            )[1],
            edit_inline=True,
        )

    async def _confirm_restart(self, callback: CallbackQuery, role: str) -> None:
        if role != ROLE_ADMIN:
            await callback.answer("Только для администратора.", show_alert=True)
            return
        await self._send_response(
            callback,
            "Перезапустить Telegram-бота?",
            reply_markup=self._inline_keyboard(
                [[("Перезапустить", "action:bot.restart")], [(BUTTON_BACK, "nav:back")]]
            ),
            edit_inline=True,
        )

    async def _restart_from_callback(self, callback: CallbackQuery, role: str) -> None:
        if role != ROLE_ADMIN:
            await callback.answer("Только для администратора.", show_alert=True)
            return
        if callback.message is not None:
            await callback.message.answer("Перезапускаю бота...")
        await callback.answer()
        await self._notify_system_event(
            f"Telegram-бот перезапускается. Администратор: {callback.from_user.id}"
        )
        asyncio.create_task(self.restart())

    async def _toggle_notification_callback(
        self,
        callback: CallbackQuery,
        key: str,
        role: str,
    ) -> None:
        if role != ROLE_ADMIN:
            await callback.answer("Только для администратора.", show_alert=True)
            return
        self._toggle_notification(callback.from_user.id, key)
        text, markup = self._notifications_screen(callback.from_user.id)
        await self._send_response(callback, text, reply_markup=markup, edit_inline=True)

    async def _start_server(self, message: Message, role: str) -> None:
        try:
            await self.manager.start()
            await message.answer(
                "Сервер запускается...",
                reply_markup=self._main_keyboard(role),
            )
            await self._notify_server_start(
                role,
                "тг бота",
                message.from_user.id if message.from_user else None,
            )
        except (RuntimeError, ValueError, FileNotFoundError) as exc:
            await message.answer(
                f"Не удалось запустить сервер: {exc}",
                reply_markup=self._main_keyboard(role),
            )

    async def _stop_server(self, message: Message) -> None:
        await self.manager.stop()
        await message.answer("Сервер остановлен.", reply_markup=self._main_keyboard(ROLE_ADMIN))

    async def _send_online(self, message: Message) -> None:
        if not self._server_is_online():
            await message.answer("Сервер не запущен.")
            return
        response = await self._send_command_and_wait("list", timeout=5)
        await message.answer(response or "Команда list отправлена. Ответ появится в логах.")

    async def _send_console_command(self, message: Message, command: str) -> None:
        if not command:
            await message.answer("Команда не задана.")
            return
        try:
            await self.manager.send_stdin_command(command)
            await message.answer("Команда отправлена.")
        except RuntimeError as exc:
            await message.answer(f"Команда не отправлена: {exc}")

    async def _send_command_and_wait(self, command: str, timeout: float) -> str:
        queue = self.log_buffer.subscribe()
        try:
            await self.manager.send_stdin_command(command)
            while True:
                item = await asyncio.wait_for(queue.get(), timeout=timeout)
                line = str(item.get("line", ""))
                if item.get("stream") == "stdout" and line and not line.startswith(">"):
                    return line
        except asyncio.TimeoutError:
            return ""
        except RuntimeError as exc:
            return f"Команда не отправлена: {exc}"
        finally:
            self.log_buffer.unsubscribe(queue)

    def _server_is_online(self) -> bool:
        status = self.manager.get_status().get("status")
        return status in {ServerStatus.RUNNING.value, ServerStatus.STARTING.value}

    @staticmethod
    def _main_title(role: str) -> str:
        return "Главная админа" if role == ROLE_ADMIN else "Главная пользователя"

    def _status_text(self) -> str:
        data = self.manager.get_work_data()
        active = data.get("active_server") or {}
        metrics = data.get("metrics") or {}
        system = metrics.get("system") or {}
        process = metrics.get("process") or {}
        minecraft = metrics.get("minecraft") or {}
        status = data.get("status", "OFF")
        name = active.get("display_name") or active.get("id") or "не выбран"
        uptime = data.get("uptime_seconds") or 0
        lines = [
            f"Сервер: {name}",
            f"Статус: {status}",
            f"Uptime: {self._format_seconds(float(uptime))}",
        ]
        if system.get("available"):
            java_cpu = process.get("cpu_percent", "-") if process.get("is_running") else "-"
            java_ram = process.get("ram_rss_mb", "-") if process.get("is_running") else "-"
            lines.extend(
                [
                    f"CPU VM: {system.get('cpu_percent', '-')}%",
                    "RAM VM: "
                    f"{system.get('ram_used_mb', '-')} MB / "
                    f"{system.get('ram_total_mb', '-')} MB",
                    f"Java CPU: {java_cpu}%",
                    f"Java RAM: {java_ram} MB",
                    f"TPS: {minecraft.get('tps') or '-'}",
                ]
            )
        if data.get("start_error"):
            lines.append(f"Ошибка запуска: {data['start_error']}")
        return "\n".join(lines)

    @staticmethod
    def _format_seconds(value: float) -> str:
        seconds = max(0, int(value))
        hours, rest = divmod(seconds, 3600)
        minutes, seconds = divmod(rest, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
