import asyncio
import json
import os
import uuid
from multiprocessing.connection import Connection

from aiogram.utils.keyboard import InlineKeyboardBuilder, KeyboardBuilder
from dotenv import load_dotenv
from functools import wraps

from aiogram.types import Message, InlineKeyboardMarkup
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, CallbackQuery
from anyio import to_process
from aiogram.filters import StateFilter

from app.core.paths import config_path
from app.core import db
from app.services.localization import Locales
from app.services.keyboards import Keyboard

kb = Keyboard()
loc = Locales(default_language="ru")
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
        self.profile_info = {"reg": False}
        self._response_task = None
        self.server_info = {"status": False}

    async def _state_updater(self):
        while True:
            try:
                msg = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ''}
                ans = await self.request(msg)
                self.server_info.update(ans["data"])
            except Exception as exc:
                print(f"Ошибка обновления состояния сервера: {exc}")

            await asyncio.sleep(5)

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
        self.dp.message.register(self.language, Command("language"))

        self.dp.callback_query.register(
            self.select_lang,
            F.data.startswith("lang:")
        )

        self.dp.message.register(self.actions_filter)

    async def actions_filter(self, message: Message, state: FSMContext):
        if self.profile_info["reg"] :
            action = loc.get_button_key(message.text, self.profile_info["language"])

            if action:
                if action == "exit":
                    await self.start(message, state)

                if self.profile_info["status"] == 1:
                    if action == "reload_bot":
                        await self.reload_bot(message, state)
                    elif action == "start_server":
                        await self.start_server(message, state)
                    elif  action == "stop_server":
                        await self.stop_server(message, state)
                    elif action == "workload":
                        await self.workload(message, state)
                    elif action == "chek_online":
                        await self.chek_online(message, state)
                    elif action == "settings_menu":
                        await message.answer("Настройки: ", kb.get_keyboard("settings_menu1", self.profile_info, self.server_info))
                    elif action == "next_settings_menu":
                        await message.answer("Доп. настройки: ", kb.get_keyboard("settings_menu2", self.profile_info, self.server_info))
                    elif action == "back":
                        await message.answer("Настройки: ", kb.get_keyboard("settings_menu1", self.profile_info, self.server_info))

                    else:
                        await message.answer("Неизвестная команда!")
                elif self.profile_info["status"] == 0:
                    if action == "start_server":
                        await self.start_server(message, state)
                    elif action == "chek_online":
                        await self.chek_online(message, state)

                    else:
                        await message.answer("Неизвестная команда!")
                else:
                    await message.answer("Чяво блять?!!! Как это нахуй сюда ты произошло?!!!")
            else:
                await message.answer("Неизвестная команда!")
        else:
            await message.answer("Вы не зарегистрированы! Введите /start")
        return

    async def start_server(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "set_server_status", "data": True}
        msg2 = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ''}
        ans = await self.request(msg)
        if "dabble_start_flag" in ans:
            if ans["dabble_start_flag"] == True:
                self.server_info["status"] = True
                await message.answer("Сервер уже запущен!",
                                     reply_markup=kb.get_keyboard("main_menu", self.profile_info, self.server_info))
            elif ans["dabble_start_flag"] == False:
                await message.answer("Сервер запускается...")
                ans2 = await self.request(msg2)
                if ans2["data"]["start_error"] != '':
                    self.server_info["status"] = False
                    await  self.bot.send_message(message.chat.id, "Ошибка запуска :\n\n"+ans2["data"]["start_error"])
                else:
                    self.server_info["status"] = True
                    await self.bot.send_message(chat_id=message.chat.id,
                                                text=f"Время запуска запуска: {ans2['data']['launch_time_str']}",
                                                reply_markup=kb.get_keyboard("main_menu", self.profile_info, self.server_info))

    async def stop_server(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "set_server_status", "data": False}
        msg2 = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ''}
        ans2 = await self.request(msg2)
        if ans2["data"]["status"] == False:
            self.server_info["status"] = False
            await message.answer(f"Сервер уже выключен!",
                                 reply_markup=kb.get_keyboard("main_menu", self.profile_info, self.server_info))
        else:
            ans = await self.request(msg)
            self.server_info["status"] = False
            await message.answer(f"Сервер остановлен! \nВремя последнего сеанса: {str(ans2['data']['work_time_str'])}",
                                 reply_markup=kb.get_keyboard("main_menu", self.profile_info, self.server_info))


    async def workload(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ''}
        ans = await self.request(msg)
        work_data = ans.get("data", {}) if isinstance(ans, dict) else {}

        system_metrics = work_data.get("system_metrics", {}) if isinstance(work_data, dict) else {}
        process_metrics = work_data.get("server_process_metrics", {}) if isinstance(work_data, dict) else {}

        sys_cpu = system_metrics.get("cpu_percent", "")
        sys_ram_used = system_metrics.get("ram_used_gb", "")
        sys_ram_total = system_metrics.get("ram_total_gb", "")
        sys_ram_percent = system_metrics.get("ram_percent", "")

        process_running = bool(process_metrics.get("is_running"))
        proc_cpu = process_metrics.get("cpu_percent", "")
        proc_ram_used = process_metrics.get("ram_rss_gb", "")
        proc_ram_percent_sys = process_metrics.get("ram_percent_of_system", "")
        proc_ram_percent_xmx = process_metrics.get("ram_percent_of_xmx", "")
        proc_xmx = process_metrics.get("xmx_gb", "") or work_data.get("server_xmx_gb", "")
        server_tps = work_data.get("server_tps", "") if isinstance(work_data, dict) else ""

        def _fmt_percent(value):
            if isinstance(value, (int, float)):
                return f"{value:.1f}%"
            return "N/A"

        def _fmt_gb(value):
            if isinstance(value, (int, float)):
                return f"{value:.2f}"
            return "N/A"

        cpu_line = f"🧠 CPU (система\\сервер): {_fmt_percent(sys_cpu)} \\ {_fmt_percent(proc_cpu) if process_running else 'N/A'}"

        sys_ram_text = (
            f"{_fmt_gb(sys_ram_used)}/{_fmt_gb(sys_ram_total)} GB ({_fmt_percent(sys_ram_percent)})"
        )

        if process_running:
            if isinstance(proc_xmx, (int, float)) and proc_xmx > 0:
                proc_ram_text = (
                    f"{_fmt_gb(proc_ram_used)}/{_fmt_gb(proc_xmx)} GB "
                    f"({_fmt_percent(proc_ram_percent_xmx)} от xmx, {_fmt_percent(proc_ram_percent_sys)} от RAM ПК)"
                )
            else:
                proc_ram_text = f"{_fmt_gb(proc_ram_used)} GB ({_fmt_percent(proc_ram_percent_sys)} от RAM ПК)"
        else:
            proc_ram_text = "N/A (сервер выключен)"

        if process_running:
            if isinstance(server_tps, dict) and isinstance(server_tps.get("value"), (int, float)):
                tps_text = (
                    f"{server_tps['value']:.2f} "
                    f"({server_tps.get('ticks', 'N/A')} ticks / {server_tps.get('seconds', 'N/A')} sec)"
                )
            else:
                tps_text = "N/A (замер ещё не завершён)"
        else:
            tps_text = "N/A (сервер выключен)"

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
            f"{cpu_line}\n"
            f"💾 RAM (система\\сервер): {sys_ram_text} \\ {proc_ram_text}\n"
            f"⏱️ TPS: {tps_text}\n"
            f"{gpu_text}"
        )

        await message.answer(workload_text)


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

    async def language(self, message: Message, state: FSMContext):
        text, text2  = loc.get_languages_data()
        builder = InlineKeyboardBuilder()
        for k, v in text2.items():
            builder.button(text=k, callback_data=f"lang:{v}")

        builder.adjust(1)
        await message.answer("Select language :", reply_markup=builder.as_markup())

    async def select_lang(self, callback: CallbackQuery):
        await callback.answer()

        lang_key = callback.data.split(":")[1]

        ##############################################
        # внести сохранение языка
        ##############################################

        await callback.message.answer(f"Lang selected: {lang_key}")


    async def start(self, message: Message, state: FSMContext):
        user_id = message.from_user.id
        user_name = message.from_user.username
        user = db.getlist("tg_id", user_id)
        if not user:
            user = db.set("tg_id", "tg_nickname", "status", "language",  user_id, user_name,0, "ru")
            db.change("tg_id", user_id, "tg_nickname", 0)
            user = db.getlist("tg_id", user_id)
            await self.language(message, state)
        self.profile_info = {"status": user["status"] if str(message.from_user.id) == str(VANILLA) else 0,
                             "userid": message.from_user.id, "game_nickname": user["game_nickname"],
                             "language": user["language"], "reg": True}
        if self.profile_info["status"] == 1:
            await state.set_state(States.admin_main_menu)
            await message.answer(
                f"Выберите действие: {self.profile_info, self.server_info}",
                reply_markup=kb.get_keyboard("main_menu", self.profile_info, self.server_info))
        elif self.profile_info["status"] == 0:
            await state.set_state(States.user_main_menu)
            await message.answer(
           "Выберите действие: ",
                reply_markup=kb.get_keyboard("main_menu", self.profile_info, self.server_info))

    async def run(self):
        try:
            self._response_task = asyncio.create_task(self._response_listener())
            self._state_updater_task = asyncio.create_task(self._state_updater())

            print("Bot successfully started...")
            try:
                await self.bot.send_message(1007806948, "Bot successfully started... /start")
            except TelegramNetworkError as exc:
                print(f"Не удалось отправить стартовое сообщение в Telegram: {exc}")

            await self.dp.start_polling(self.bot)

        except Exception as exc:
            print(f"Ошибка в боте: {exc}")
            import traceback
            self.conn.send({"to_process": "GUI", "from_process": "bot", "command": "error_out","data": traceback.format_exc()})
            traceback.print_exc()
        finally:
            if self._response_task:
                self._response_task.cancel()
            if getattr(self, "_state_updater_task", None):
                self._state_updater_task.cancel()
            await self.bot.session.close()
            print("Бот остановлен")


def run_bot(conn: Connection):
    with config_path("program_settings.json").open("r", encoding="utf-8") as file:
        settings = json.load(file)
    token = BOT_TOKEN or settings["telegram_bot_token"]
    asyncio.run(Bott(token, conn).run())
