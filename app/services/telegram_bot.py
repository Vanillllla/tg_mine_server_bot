import asyncio
import json
import os
import uuid
from functools import wraps
from multiprocessing.connection import Connection

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv

from app.core import db
from app.core.paths import config_path
from app.services.bot_ui import build_keyboard, get_message, is_action_text, normalize_locale

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
            await message.answer(self._msg(message, "server_off"))
            return

        command = await func(self, message, *args, **kwargs)
        if not command:
            await message.answer(self._msg(message, "command_not_set"))
            return

        msg = {
            "to_process": "server",
            "from_process": "bot",
            "command": "server_rcon_command",
            "data": command,
        }

        ans = await self.request(msg)
        await message.answer(str(ans["data"]))

    return wrapper


class BotKeyboards:
    @staticmethod
    def get_keyboard(
        status: int = 0,
        server_status: bool = False,
        menu: str = "main_menu",
        locale: str = "ru",
    ) -> ReplyKeyboardMarkup | None:
        return build_keyboard(
            status=status,
            server_status=server_status,
            menu=menu,
            locale=locale,
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
        self.vanilla = VANILLA if VANILLA else None
        self.pending = {}
        self.user_locales = {}
        self._response_task = None
        self.server_info = {"status": False}
        self._register_handlers()

    @staticmethod
    def _button_filter(action_id: str):
        def _filter(message: Message) -> bool:
            return is_action_text(action_id, getattr(message, "text", None))

        return _filter

    def _set_user_locale(self, user_id: int, tg_language_code: str | None):
        self.user_locales[user_id] = normalize_locale(tg_language_code)

    def _resolve_locale(self, message: Message) -> str:
        user_id = message.from_user.id if message.from_user else None
        if user_id is not None and user_id in self.user_locales:
            return self.user_locales[user_id]

        tg_language_code = message.from_user.language_code if message.from_user else None
        locale = normalize_locale(tg_language_code)
        if user_id is not None:
            self.user_locales[user_id] = locale
        return locale

    def _msg(self, message: Message, key: str, **kwargs) -> str:
        return get_message(self._resolve_locale(message), key, **kwargs)

    def _keyboard(
        self,
        message: Message,
        status: int,
        server_status: bool = False,
        menu: str = "main_menu",
    ) -> ReplyKeyboardMarkup | None:
        return BotKeyboards.get_keyboard(
            status=status,
            server_status=server_status,
            menu=menu,
            locale=self._resolve_locale(message),
        )

    @staticmethod
    def _is_action(message: Message, action_id: str) -> bool:
        return is_action_text(action_id, getattr(message, "text", None))

    async def _state_updater(self):
        while True:
            try:
                msg = {
                    "to_process": "server",
                    "from_process": "bot",
                    "command": "get_server_work_data",
                    "data": "",
                }
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
        self.dp.message.register(
            self.start_server,
            self._button_filter("start_server"),
            StateFilter(States.user_main_menu, States.admin_main_menu),
        )
        self.dp.message.register(
            self.stop_server,
            self._button_filter("stop_server"),
            StateFilter(States.admin_main_menu),
        )
        self.dp.message.register(
            self.reload_bot,
            self._button_filter("reload_bot"),
            StateFilter(States.admin_main_menu),
        )
        self.dp.message.register(
            self.settings_open,
            self._button_filter("admin_settings"),
            StateFilter(States.admin_main_menu),
        )
        # self.dp.message.register(self., self._button_filter("server_properties"), StateFilter(States.admin_settings))
        self.dp.message.register(
            self.workload,
            self._button_filter("workload"),
            StateFilter(States.admin_settings),
        )
        self.dp.message.register(
            self.settings_close,
            self._button_filter("back"),
            StateFilter(States.admin_settings),
        )
        self.dp.message.register(
            self.chek_online,
            self._button_filter("online"),
            StateFilter(States.admin_main_menu, States.user_main_menu),
        )
        self.dp.message.register(
            self.console_mode,
            self._button_filter("console"),
            StateFilter(States.admin_main_menu),
        )
        self.dp.message.register(
            self.noname_main_menu,
            StateFilter(States.user_main_menu, States.admin_main_menu),
        )
        self.dp.message.register(self.noname_settings_menu, StateFilter(States.admin_settings))
        self.dp.message.register(self.console_mode_write, StateFilter(States.admin_console))

        self.dp.message.register(self.noname_no_auth)

    async def server_switch(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "set_server_status", "data": True}
        self.pipe_send(msg)

    async def start_server(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "set_server_status", "data": True}
        msg2 = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ""}
        ans = await self.request(msg)

        if "dabble_start_flag" in ans:
            if ans["dabble_start_flag"] is True:
                self.server_info["status"] = True
                await message.answer(
                    self._msg(message, "server_already_running"),
                    reply_markup=self._keyboard(
                        message=message,
                        status=self.profile_info["status"],
                        server_status=self.server_info["status"],
                    ),
                )
            elif ans["dabble_start_flag"] is False:
                await message.answer(self._msg(message, "server_starting"))
                ans2 = await self.request(msg2)
                if ans2["data"]["start_error"] != "":
                    self.server_info["status"] = False
                    await self.bot.send_message(
                        message.chat.id,
                        self._msg(message, "start_error_prefix") + ans2["data"]["start_error"],
                    )
                else:
                    self.server_info["status"] = True
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text=self._msg(message, "start_time", launch_time=ans2["data"]["launch_time_str"]),
                        reply_markup=self._keyboard(
                            message=message,
                            status=self.profile_info["status"],
                            server_status=self.server_info["status"],
                        ),
                    )

    async def stop_server(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "set_server_status", "data": False}
        msg2 = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ""}
        ans2 = await self.request(msg2)

        if ans2["data"]["status"] is False:
            self.server_info["status"] = False
            await message.answer(
                self._msg(message, "server_already_off"),
                reply_markup=self._keyboard(
                    message=message,
                    status=self.profile_info["status"],
                    server_status=self.server_info["status"],
                ),
            )
        else:
            await self.request(msg)
            self.server_info["status"] = False
            await message.answer(
                self._msg(message, "server_stopped", work_time=str(ans2["data"]["work_time_str"])),
                reply_markup=self._keyboard(
                    message=message,
                    status=self.profile_info["status"],
                    server_status=self.server_info["status"],
                ),
            )

    async def settings_open(self, message: Message, state: FSMContext):
        await state.set_state(States.admin_settings)
        await message.answer(
            self._msg(message, "settings_panel"),
            reply_markup=self._keyboard(
                message=message,
                status=self.profile_info["status"],
                menu="settings",
            ),
        )

    async def workload(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "get_server_work_data", "data": ""}
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

        cpu_line = self._msg(
            message,
            "cpu_line",
            sys_cpu=_fmt_percent(sys_cpu),
            proc_cpu=_fmt_percent(proc_cpu) if process_running else "N/A",
        )

        sys_ram_text = f"{_fmt_gb(sys_ram_used)}/{_fmt_gb(sys_ram_total)} GB ({_fmt_percent(sys_ram_percent)})"

        if process_running:
            if isinstance(proc_xmx, (int, float)) and proc_xmx > 0:
                proc_ram_text = self._msg(
                    message,
                    "ram_server_part",
                    used=_fmt_gb(proc_ram_used),
                    total=_fmt_gb(proc_xmx),
                    pct=_fmt_percent(proc_ram_percent_xmx),
                    sys_pct=_fmt_percent(proc_ram_percent_sys),
                )
            else:
                proc_ram_text = self._msg(
                    message,
                    "ram_server_part_short",
                    used=_fmt_gb(proc_ram_used),
                    sys_pct=_fmt_percent(proc_ram_percent_sys),
                )
        else:
            proc_ram_text = self._msg(message, "na_server_off")

        if process_running:
            if isinstance(server_tps, dict) and isinstance(server_tps.get("value"), (int, float)):
                tps_text = (
                    f"{server_tps['value']:.2f} "
                    f"({server_tps.get('ticks', 'N/A')} ticks / {server_tps.get('seconds', 'N/A')} sec)"
                )
            else:
                tps_text = self._msg(message, "na_measure_pending")
        else:
            tps_text = self._msg(message, "na_server_off")

        gpu_text = self._msg(message, "gpu_unavailable")
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
                gpu_mem_used_gb = mem.used / (1024**3)
                gpu_mem_total_gb = mem.total / (1024**3)

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
            f"{self._msg(message, 'workload_header')}\n"
            f"{cpu_line}\n"
            f"{self._msg(message, 'ram_line', sys_ram=sys_ram_text, proc_ram=proc_ram_text)}\n"
            f"{self._msg(message, 'tps_line', tps=tps_text)}\n"
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
        await message.answer(
            self._msg(message, "console_mode"),
            reply_markup=self._keyboard(
                message=message,
                status=self.profile_info["status"],
                menu="console",
            ),
        )

    async def console_mode_write(self, message: Message, state: FSMContext):
        if not self._is_action(message, "back"):
            await self.console_mode_send(message, state)
        else:
            await self.start(message=message, state=state)

    @send_rcon_command
    async def console_mode_send(self, message: Message, state: FSMContext):
        return str(message.text)

    async def noname_main_menu(self, message: Message):
        await message.answer(
            self._msg(message, "unknown_command"),
            reply_markup=self._keyboard(
                message=message,
                status=self.profile_info["status"],
                server_status=self.server_info["status"],
            ),
        )

    async def noname_no_auth(self, message: Message):
        await message.answer(self._msg(message, "enter_start"), reply_markup=ReplyKeyboardRemove())

    async def noname_settings_menu(self, message: Message, state: FSMContext):
        await message.answer(self._msg(message, "unknown_command_ex"))

    async def start(self, message: Message, state: FSMContext):
        user_id = message.from_user.id
        user = db.getlist("tg_id", user_id)
        if not user:
            user = db.set("tg_id", user_id, "status", 0)
            db.change("tg_id", user_id, "tg_nickname", 0)
            user = db.getlist("tg_id", user_id)

        self._set_user_locale(user_id, message.from_user.language_code if message.from_user else None)

        self.profile_info = {
            "status": user["status"] if str(message.from_user.id) == str(VANILLA) else 0,
            "userid": message.from_user.id,
            "game_nickname": user["game_nickname"],
        }

        if self.profile_info["status"] == 1:
            await state.set_state(States.admin_main_menu)
            await message.answer(
                self._msg(message, "choose_action_admin", profile_and_server=(self.profile_info, self.server_info)),
                reply_markup=self._keyboard(
                    message=message,
                    status=self.profile_info["status"],
                    server_status=self.server_info["status"],
                ),
            )
        elif self.profile_info["status"] == 0:
            await state.set_state(States.user_main_menu)
            await message.answer(
                self._msg(message, "choose_action_user"),
                reply_markup=self._keyboard(
                    message=message,
                    status=self.profile_info["status"],
                    server_status=self.server_info["status"],
                ),
            )

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

            self.conn.send(
                {
                    "to_process": "GUI",
                    "from_process": "bot",
                    "command": "error_out",
                    "data": traceback.format_exc(),
                }
            )
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
