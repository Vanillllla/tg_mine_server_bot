import asyncio
import signal
import sys
import time
from multiprocessing.connection import Connection
import json
import threading
import aiofiles
import os
import aiofiles
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

        threading.Thread(
            target=self.pipe_read,
            daemon=True
        ).start()

        print("Bot successfully started...")

    def pipe_read(self):
        while True:
            try:
                msg = self.conn.recv()
                if msg:
                    print("took massage : ", msg)
            except Exception as e:
                print("PIPE Error in bot : ", e)
            time.sleep(1)

    def pipe_send(self, msg: dict):
        if self.conn:
            self.conn.send(msg)

    def _register_handlers(self):
        # Стартовая команда
        self.dp.message.register(self.start, Command("start"))

        self.dp.message.register(self.server_switch, F.text == "переключить_сервер")

        self.dp.message.register(self.nonmess)

    async def start(self, message: Message, state: FSMContext):
        # Создаем кнопки
        kb = [
            [KeyboardButton(text="переключить_сервер")]
        ]
        keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

        await message.answer("Выберите действие:", reply_markup=keyboard)

    async def server_switch(self, message: Message, state: FSMContext):
        msg = {"to_process": "server", "command": "switch", "data": None}
        await message.answer(f"ОТПРАВЛЕНА ТЕСТОВАЯ КОМАНДА: {msg}")
        self.pipe_send(msg)

    async def nonmess(self, message: Message, state: FSMContext):
        print(message.text)

    async def run(self):
        print("run() начал выполнение")
        try:
            await self.bot.send_message(1007806948, "Bot successfully started...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            print(f"Ошибка в боте: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.bot.session.close()
            print("Бот остановлен")


def pipe_write(conn, msg: dict):
    """Асинхронная отправка сообщений в канал"""
    conn.send(msg)

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
