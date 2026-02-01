import asyncio
import signal
import sys
import time
from multiprocessing.connection import Connection
import json
import threading
import aiofiles
import uuid
import os
from aiofiles import os as aio_os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


# Состояния
class Form(StatesGroup):
    main_menu = State()
    dop_manu = State()


# Класс бота
class Bott:
    def __init__(self, token: str, conn: Connection = None):
        self.bot = Bot(token=token)
        self.conn = conn
        self.dp = Dispatcher()
        self._register_handlers()
        self.vanilla = 1007806948
        self.pending = {}  # {request_id: future}
        self._response_task = None  # Не создаем задачу здесь

        print("Bot successfully started...")

    async def request(self, data: dict, timeout: float = 30.0) -> dict:
        """Простой асинхронный запрос"""
        # 1. Создаем ID и Future
        req_id = str(uuid.uuid4())
        future = asyncio.Future()
        self.pending[req_id] = future

        # 2. Отправляем с ID
        self.conn.send({**data, "request_id": req_id})

        # 3. Ждем ответ именно с этим ID
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.pending.pop(req_id, None)
            raise

    async def _response_listener(self):
        """Фоновая задача для чтения ответов из pipe"""
        loop = asyncio.get_event_loop()

        while True:
            try:
                # Проверяем, есть ли данные для чтения
                def check_pipe():
                    if self.conn.poll(timeout=0.1):
                        return self.conn.recv()
                    return None

                # Читаем ответ в отдельном потоке
                response = await loop.run_in_executor(None, check_pipe)

                if response:
                    # print(f"📥 Получен ответ: {response}")
                    self.process_response(response)

                await asyncio.sleep(0.01)

            except EOFError:
                print("Канал закрыт")
                break
            except Exception as e:
                print(f"Ошибка в response_listener: {e}")
                await asyncio.sleep(1)

    def process_response(self, response: dict):
        """Вызывается при получении ответа из pipe"""
        req_id = response.get("request_id")
        if req_id in self.pending:
            self.pending.pop(req_id).set_result(response)

    def pipe_request(self, msg: dict):
        """Отправляет запрос через pipe и получает ответ"""
        self.conn.send(msg)
        ans = self.conn.recv()
        print(f"Received from pipe: {ans}")
        return ans

    def pipe_send(self, msg: dict):
        """Отправляет сообщение через pipe без ожидания ответа"""
        if self.conn:
            self.conn.send(msg)

    def _register_handlers(self):
        # Стартовая команда
        self.dp.message.register(self.start, Command("start"))
        self.dp.message.register(self.server_switch, F.text == "переключить_сервер")
        self.dp.message.register(self.nonmess)

    async def start(self, message: Message, state: FSMContext):
        # self.login()
        kb = [
            [KeyboardButton(text="Запустить сервер"), KeyboardButton(text="Остановить сервер")],
            [KeyboardButton(text="Просто кнопка))) (причём широкая)")]
        ]
        await message.answer("Выберите действие:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

    async def server_switch(self, message: Message, state: FSMContext):
       pass

    async def nonmess(self, message: Message, state: FSMContext):
        await message.answer("Пиши па русски! Что ты хотел?!")

    async def run(self):
        try:
            self._response_task = asyncio.create_task(self._response_listener())

            await self.bot.send_message(1007806948, "Bot successfully started...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            print(f"Ошибка в боте: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Отменяем фоновую задачу при завершении
            if self._response_task:
                self._response_task.cancel()
            await self.bot.session.close()
            print("Бот остановлен")


def run_bot(conn: Connection):
    """Точка входа для multiprocessing"""
    print("Trying to start bot.py")
    with open('program_settings.json', 'r', encoding='utf-8') as f:
        settings = json.load(f)
    token = BOT_TOKEN or settings["telegram_bot_token"]
    bot = Bott(token, conn)

    # Запускаем асинхронный цикл
    asyncio.run(bot.run())
    print("Бот завершил работу")