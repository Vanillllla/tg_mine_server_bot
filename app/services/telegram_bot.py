import asyncio
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.models.server import ServerStatus
from app.services.log_buffer import LogBuffer
from app.services.minecraft_manager import MinecraftServerManager
from app.services.panel_settings import PanelSettingsService


BUTTON_START = "Запустить сервер"
BUTTON_STOP = "Остановить сервер"
BUTTON_STATUS = "Статус"
BUTTON_ONLINE = "Онлайн"
BUTTON_METRICS = "Нагрузка"
BUTTON_CONSOLE = "Консоль"
BUTTON_EXIT = "Выйти из консоли"


class TelegramBotStates(StatesGroup):
    console = State()


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
        return {
            "running": self.is_running,
            "last_error": self._last_error,
            "configured": bool(settings.bot_token),
            "admin_count": len(settings.admin_ids),
        }

    def _capture_polling_error(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        try:
            task.result()
        except Exception as exc:
            self._last_error = str(exc)

    def _register_handlers(self, dispatcher: Dispatcher) -> None:
        dispatcher.message.register(self._start, Command("start"))
        dispatcher.message.register(self._handle_message)

    def _main_keyboard(self) -> ReplyKeyboardMarkup:
        status = self.manager.get_status()["status"]
        toggle_button = BUTTON_STOP if status == ServerStatus.RUNNING.value else BUTTON_START
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=toggle_button), KeyboardButton(text=BUTTON_STATUS)],
                [KeyboardButton(text=BUTTON_ONLINE), KeyboardButton(text=BUTTON_METRICS)],
                [KeyboardButton(text=BUTTON_CONSOLE)],
            ],
            resize_keyboard=True,
        )

    @staticmethod
    def _console_keyboard() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=BUTTON_EXIT)]],
            resize_keyboard=True,
        )

    def _is_admin(self, message: Message) -> bool:
        user = message.from_user
        return user is not None and user.id in self._admin_ids

    async def _deny_if_not_admin(self, message: Message) -> bool:
        if self._is_admin(message):
            return False
        user_id = message.from_user.id if message.from_user else "unknown"
        await message.answer(f"Доступ запрещен. Ваш Telegram ID: {user_id}")
        return True

    async def _start(self, message: Message, state: FSMContext) -> None:
        if await self._deny_if_not_admin(message):
            return
        await state.clear()
        await message.answer("Выберите действие:", reply_markup=self._main_keyboard())

    async def _handle_message(self, message: Message, state: FSMContext) -> None:
        if await self._deny_if_not_admin(message):
            return

        text = (message.text or "").strip()
        if await state.get_state() == TelegramBotStates.console.state:
            if text == BUTTON_EXIT:
                await state.clear()
                await message.answer("Консоль закрыта.", reply_markup=self._main_keyboard())
                return
            await self._send_console_command(message, text)
            return

        if text == BUTTON_START:
            await self._start_server(message)
        elif text == BUTTON_STOP:
            await self._stop_server(message)
        elif text == BUTTON_STATUS:
            await message.answer(self._status_text(), reply_markup=self._main_keyboard())
        elif text == BUTTON_ONLINE:
            await self._send_list_command(message)
        elif text == BUTTON_METRICS:
            await message.answer(self._metrics_text())
        elif text == BUTTON_CONSOLE:
            await state.set_state(TelegramBotStates.console)
            await message.answer("Режим консоли. Отправьте команду серверу.", reply_markup=self._console_keyboard())
        else:
            await message.answer("Неизвестная команда.", reply_markup=self._main_keyboard())

    async def _start_server(self, message: Message) -> None:
        try:
            await self.manager.start()
            await message.answer("Сервер запускается...", reply_markup=self._main_keyboard())
        except (RuntimeError, ValueError, FileNotFoundError) as exc:
            await message.answer(f"Не удалось запустить сервер: {exc}", reply_markup=self._main_keyboard())

    async def _stop_server(self, message: Message) -> None:
        await self.manager.stop()
        await message.answer("Сервер остановлен.", reply_markup=self._main_keyboard())

    async def _send_list_command(self, message: Message) -> None:
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

    def _status_text(self) -> str:
        data = self.manager.get_work_data()
        active = data.get("active_server") or {}
        status = data.get("status", "OFF")
        name = active.get("display_name") or active.get("id") or "не выбран"
        uptime = data.get("uptime_seconds") or 0
        return f"Сервер: {name}\nСтатус: {status}\nUptime: {uptime:.0f}s"

    def _metrics_text(self) -> str:
        data = self.manager.get_metrics()
        system = data.get("system", {})
        process = data.get("process", {})
        minecraft = data.get("minecraft", {})
        if not system.get("available"):
            return "Метрики системы недоступны."
        lines = [
            f"CPU VM: {system.get('cpu_percent', '-')}%",
            f"RAM VM: {system.get('ram_used_mb', '-')} MB ({system.get('ram_percent', '-')}%)",
            f"Java CPU: {process.get('cpu_percent', '-') if process.get('is_running') else '-'}%",
            f"Java RAM: {process.get('ram_rss_mb', '-') if process.get('is_running') else '-'} MB",
            f"TPS: {minecraft.get('tps') or '-'}",
        ]
        return "\n".join(lines)
