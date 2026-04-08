import asyncio
import json
import os
import uuid
from multiprocessing.connection import Connection

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv

from app.core.paths import config_path

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
VANILLA = os.getenv("VANILLA")

class Form(StatesGroup):
    main_menu = State()
    dop_manu = State()


class Bott:
    def __init__(self, token: str, conn: Connection = None):
        self.bot = Bot(token=token)
        self.conn = conn
        self.dp = Dispatcher()
        self._register_handlers()
        self.vanilla = VANILLA if VANILLA else None
        self.pending = {}
        self._response_task = None

    async def request(self, data: dict, timeout: float = 30.0) -> dict:
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
        # self.dp.message.register(self.start_server, F.text == "Запустить сервер")
        self.dp.message.register(self.server_switch, F.text == "переключить_сервер")
        self.dp.message.register(self.nonmess)

    async def start(self, message: Message, state: FSMContext):
        # self.state = await state.set_state(???)
        keyboard = [
            [KeyboardButton(text="Запустить сервер"), KeyboardButton(text="Остановить сервер")],
            [KeyboardButton(text="переключить_сервер")],
        ]
        await message.answer(
            "Выберите действие:",
            reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True),
        )

    async def server_switch(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "from_process": "bot", "command": "set_server_status", "data": True}
        self.pipe_send(msg)

    async def nonmess(self, message: Message, state: FSMContext):
        await message.answer("Отправлена команда : " + message.text)
        self.pipe_send(
            {
                "to_process": "server",
                "from_process": "bot",
                "command": "server_command",
                "data": message.text,
            }
        )

    async def run(self):
        try:
            self._response_task = asyncio.create_task(self._response_listener())
            print("Bot successfully started...")
            await self.bot.send_message(1007806948, "Bot successfully started...")
            await self.dp.start_polling(self.bot)
        except Exception as exc:
            print(f"Ошибка в боте: {exc}")
            import traceback

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
