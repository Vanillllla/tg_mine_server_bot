import asyncio
import json
import os
import time
import uuid
from multiprocessing.connection import Connection
from dotenv import load_dotenv
from functools import wraps
import psutil

from aiogram.types import Message
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from anyio import to_process
from aiogram.filters import StateFilter

from app.core.paths import config_path

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
VANILLA = os.getenv("VANILLA")

try:
    import pynvml  # pip install nvidia-ml-py3
    _HAS_NVML = True
except Exception:
    _HAS_NVML = False

def send_rcon_command(func):
    @wraps(func)
    async def wrapper(self, message: Message, *args, **kwargs):
        if self.server_info["status"] != 1:
            await message.answer("Сервер выключен!")
            return

        command = await func(self, message, *args, **kwargs)

        if not command:
            await message.answer("Команда не задана")
            return

        msg = {
            "to_process": "server",
            "from_process": "bot",
            "command": "server_rcon_command",
            "data": command
        }

        ans = await self.request(msg)
        await message.answer(str(ans["data"]))

    return wrapper

class BotKeyboards:
    @staticmethod
    def get_keyboard(status: int = 0, server_status: bool = False,
                     menu: str = "main_menu") -> ReplyKeyboardMarkup:
        if status == 0:
            if menu == "main_menu":
                return BotKeyboards.user_main(server_status)
            elif menu == "settings":
                return BotKeyboards.user_settings()
        if status == 1:
            if menu in {"main", "main_menu"}:
                return BotKeyboards.admin_main(server_status)
            elif menu == "settings":
                return BotKeyboards.admin_settings()
            elif menu == "console":
                return BotKeyboards.admin_console()

    @staticmethod
    def user_main(server_status: bool = False) -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text=("🚀 Запустить сервер" if not server_status else "👥 Онлайн на сервере"))],
            [KeyboardButton(text="⚙️ Мои настройки"), KeyboardButton(text="test")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def user_settings() -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def admin_main(server_status: bool = False) -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text="🟢 Запустить сервер 🟢") if not server_status else KeyboardButton(
                text="🔴 Остановить сервер 🔴")],
            [KeyboardButton(text="👥 Онлайн на сервере"), KeyboardButton(text="📟 Консоль")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="🔄 Перезапустить бота")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def admin_console() -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text="⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def admin_settings(notifications_enabled: bool = True) -> ReplyKeyboardMarkup:
        notify_button = (
            "🟢 Выключить уведомления о запуске"
            if notifications_enabled
            else "🔴 Включить уведомления о запуске"
        )

        keyboard = [
            [KeyboardButton(text="🧩 Server properties"), KeyboardButton(text="📊 Нагрузка сервера")],
            # [KeyboardButton(text="👤 Пользователи бота")],
            # [KeyboardButton(text=notify_button)],
            [KeyboardButton(text="⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def admin_users() -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text="📋 Список пользователей")],
            [KeyboardButton(text="➕ Добавить пользователя"), KeyboardButton(text="➖ Удалить пользователя")],
            [KeyboardButton(text="🔒 Права доступа")],
            [KeyboardButton(text="⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )


class States(StatesGroup):
    user_main_menu = State()
    user_dop_manu = State()
    admin_main_menu = State()
    admin_settings = State()
    admin_console = State()
    admin_dop_manu = State()


class Bott:
    def __init__(self, token: str, conn: Connection = None):
        self.bot = Bot(token=token)
        self.conn = conn
        self.dp = Dispatcher()
        self._register_handlers()
        self.vanilla = VANILLA if VANILLA else None
        self.pending = {}
        self._response_task = None
        self.server_info = {"status": False}

    async def _state_updater(self):
        msg = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ''}
        ans = await self.request(msg)
        self.server_info.update(ans["data"])
        time.sleep(5)

    async def request(self, data: dict, timeout: float = 90.0) -> dict:
        req_id = str(uuid.uuid4())
        future = asyncio.Future()
        self.pending[req_id] = future
        self.conn.send({**data, "request_id": req_id})
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.pending.pop(req_id, None)
            raise

    async def _response_listener(self):
        loop = asyncio.get_event_loop()
        while True:
            try:
                def check_pipe():
                    if self.conn.poll(timeout=0.1):
                        return self.conn.recv()
                    return None

                response = await loop.run_in_executor(None, check_pipe)
                if response:
                    self.process_response(response)
                await asyncio.sleep(0.01)
            except EOFError:
                print("Канал закрыт")
                break
            except Exception as exc:
                print(f"Ошибка в response_listener: {exc}")
                await asyncio.sleep(1)

    def process_response(self, response: dict):
        req_id = response.get("request_id")
        if req_id in self.pending:
            self.pending.pop(req_id).set_result(response)

    def pipe_send(self, msg: dict):
        if self.conn:
            self.conn.send(msg)

    def _register_handlers(self):
        self.dp.message.register(self.start, Command("start"))
        self.dp.message.register(self.start_server, F.text.in_(["🚀 Запустить сервер", "🟢 Запустить сервер 🟢"]),
                                 StateFilter(States.user_main_menu, States.admin_main_menu))
        self.dp.message.register(self.stop_server, F.text == "🔴 Остановить сервер 🔴",
                                 StateFilter(States.admin_main_menu))
        self.dp.message.register(self.reload_bot, F.text == "🔄 Перезапустить бота", StateFilter(States.admin_main_menu))
        self.dp.message.register(self.settings_open, F.text == "⚙️ Настройки", StateFilter(States.admin_main_menu))
        # self.dp.message.register(self., F.text == "🧩 Server properties", StateFilter(States.admin_settings))
        self.dp.message.register(self.workload, F.text == "📊 Нагрузка сервера", StateFilter(States.admin_settings))
        self.dp.message.register(self.settings_close, F.text == "⬅️ Назад", StateFilter(States.admin_settings))
        self.dp.message.register(self.chek_online, F.text == "👥 Онлайн на сервере",
                                 StateFilter(States.admin_main_menu,     States.user_main_menu))
        self.dp.message.register(self.console_mode, F.text == "📟 Консоль", StateFilter(States.admin_main_menu))
        self.dp.message.register(self.noname_main_menu, StateFilter(States.user_main_menu, States.admin_main_menu))
        self.dp.message.register(self.noname_settings_menu, StateFilter(States.admin_settings))
        self.dp.message.register(self.console_mode_write, StateFilter(States.admin_console))


        self.dp.message.register(self.noname_no_auth)

    async def server_switch(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "set_server_status", "data": True}
        self.pipe_send(msg)

    async def start_server(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "set_server_status", "data": True}
        msg2 = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ''}
        ans = await self.request(msg)
        if "dabble_start_flag" in ans:
            if ans["dabble_start_flag"] == True:
                self.server_info["status"] = True
                await message.answer("Сервер уже запущен!",
                                     reply_markup=BotKeyboards.get_keyboard(status=self.profile_info["status"],
                                                                            server_status=self.server_info[
                                                                                "status"]))
            elif ans["dabble_start_flag"] == False:
                await message.answer("Сервер запускается...")
                ans2 = await self.request(msg2)
                if ans2["data"]["start_error"] != '':
                    self.server_info["status"] = False
                    await  self.bot.send_message(message.chat.id, "Ошибка запуска :\n\n"+ans2["data"]["start_error"])
                else:
                    self.server_info["status"] = True
                    await self.bot.send_message(chat_id=message.chat.id,
                                                text=f"Время запуска запуска: {ans2["data"]["launch_time_str"]}",
                                                reply_markup=BotKeyboards.get_keyboard(status=self.profile_info["status"],
                                                                                       server_status=self.server_info[
                                                                                           "status"]))

    async def stop_server(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "set_server_status", "data": False}
        msg2 = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ''}
        ans2 = await self.request(msg2)
        if ans2["data"]["status"] == False:
            self.server_info["status"] = False
            await message.answer(f"Сервер уже выключен!",
                                 reply_markup=BotKeyboards.get_keyboard(status=self.profile_info["status"],
                                                                        server_status=self.server_info["status"]))
        else:
            ans = await self.request(msg)
            self.server_info["status"] = False
            await message.answer(f"Сервер остановлен! \nВремя последнего сеанса: {str(ans2["data"]["work_time_str"])}",
                                 reply_markup=BotKeyboards.get_keyboard(status=self.profile_info["status"],
                                                                        server_status=self.server_info["status"]))

    async def settings_open(self, message: Message, state: FSMContext):
        await state.set_state(States.admin_settings)
        await message.answer("Панель настроек : ", reply_markup=BotKeyboards.get_keyboard(status=self.profile_info["status"],
                                                                                          menu="settings"))

    async def workload(self, message: Message, state: FSMContext):
        # CPU "как в диспетчере задач" — за короткий интервал
        cpu_percent = psutil.cpu_percent(interval=0.5)

        # RAM
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_used_gb = ram.used / (1024 ** 3)
        ram_total_gb = ram.total / (1024 ** 3)

        # GPU (NVIDIA)
        gpu_text = "GPU: недоступно (нет NVIDIA/драйвера/библиотеки pynvml)"
        if _HAS_NVML:
            try:
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # первая видеокарта
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="ignore")

                gpu_percent = util.gpu
                gpu_mem_percent = (mem.used / mem.total) * 100
                gpu_mem_used_gb = mem.used / (1024 ** 3)
                gpu_mem_total_gb = mem.total / (1024 ** 3)

                gpu_text = (
                    f"GPU ({name}): {gpu_percent:.1f}%\n"
                    f"VRAM: {gpu_mem_used_gb:.1f}/{gpu_mem_total_gb:.1f} GB ({gpu_mem_percent:.1f}%)"
                )
            except Exception:
                pass
            finally:
                try:
                    pynvml.nvmlShutdown()
                except Exception:
                    pass

        workload_text = (
            f"📊 Нагрузка на сервер (текущий момент):\n"
            f"🧠 CPU: {cpu_percent:.1f}%\n"
            f"💾 RAM: {ram_used_gb:.1f}/{ram_total_gb:.1f} GB ({ram_percent:.1f}%)\n"
            f"{gpu_text}"
        )

        await message.answer(workload_text)

    async def settings_close(self, message: Message, state: FSMContext):
        await self.start(message=message, state=state)

    async def reload_bot(self, message: Message, state: FSMContext):
        msg = {"to_process": "connector", "from_process": "bot", "command": "reload_bot", "data": ""}
        self.pipe_send(msg)

    @send_rcon_command
    async def chek_online(self, message: Message, state: FSMContext):
        return "list"


    async def console_mode(self, message: Message, state: FSMContext):
        await state.set_state(States.admin_console)
        await message.answer("Режим консоли:", reply_markup=BotKeyboards.get_keyboard(
                                                                status=self.profile_info["status"],
                                                                menu="console"))


    async def console_mode_write(self, message: Message, state: FSMContext):
        if message.text != "⬅️ Назад":
            await self.console_mode_send(message, state)
        else:
            await self.start(message=message, state=state)

    @send_rcon_command
    async def console_mode_send(self, message: Message, state: FSMContext):
        return str(message.text)

    async def noname_main_menu(self, message: Message):
        await message.answer("Неизвестная команда",
                             reply_markup=BotKeyboards.get_keyboard(status=self.profile_info["status"],
                                                                    server_status=self.server_info["status"]))

    @staticmethod
    async def noname_no_auth(message: Message):
        await message.answer("Введите /start для входа", reply_markup=ReplyKeyboardRemove())

    async def noname_settings_menu(self, message: Message, state: FSMContext):
        await message.answer("Неизвестная команда!")

    async def start(self, message: Message, state: FSMContext):
        self.profile_info = {"status": 1 if str(message.from_user.id) == str(VANILLA) else 0,
                             "userid": message.from_user.id}

        if self.profile_info["status"] == 1:
            await state.set_state(States.admin_main_menu)
            await message.answer(
                f"Выберите действие: {self.profile_info, self.server_info}",
                reply_markup=BotKeyboards.get_keyboard(status=self.profile_info["status"],
                                                       server_status=self.server_info["status"]),
            )
        elif self.profile_info["status"] == 0:
            await state.set_state(States.user_main_menu)
            await message.answer("Выберите действие: ",
                                 reply_markup=BotKeyboards.get_keyboard(status=self.profile_info["status"],
                                                                        server_status=self.server_info["status"]))

    async def run(self):
        try:
            self._response_task = asyncio.create_task(self._response_listener())
            self._state_updater_task = asyncio.create_task(self._state_updater())

            print("Bot successfully started...")
            await self.bot.send_message(1007806948, "Bot successfully started... /start")

            await self.dp.start_polling(self.bot)

        except Exception as exc:
            print(f"Ошибка в боте: {exc}")
            import traceback
            self.conn.send({"to_process": "GUI", "from_process": "bot", "command": "error_out","data": traceback.format_exc()})
            traceback.print_exc()
        finally:
            if self._response_task:
                self._response_task.cancel()
            await self.bot.session.close()
            print("Бот остановлен")


def run_bot(conn: Connection):
    with config_path("program_settings.json").open("r", encoding="utf-8") as file:
        settings = json.load(file)
    token = BOT_TOKEN or settings["telegram_bot_token"]
    asyncio.run(Bott(token, conn).run())
