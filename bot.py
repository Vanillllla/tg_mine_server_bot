import asyncio
import signal
import sys
from multiprocessing.connection import Connection
import json
import threading
import aiofiles
import os  # Use standard os module
import aiofiles
from aiofiles import os as aio_os # Keep aiofiles separate if you need it for async file operations
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
    def __init__(self, token: str, conn: Connection = None ):
        self.bot = Bot(token=token)
        self.conn = conn
        self.dp = Dispatcher()
        self._register_handlers()
        self.init_pipes()

    def init_pipes(self):
        # thread= threading.Thread(target=self.pipe_write, args=(self.conn))
        # thread.start()
        thread = threading.Thread(target=self.pipe_read, args=(self.conn))
        thread.start()

    def pipe_read(self, conn : Connection):
        pass

    async def pipe_write(self, conn : Connection):
        pass

    def _register_handlers(self):
        # Стартовая команда
        self.dp.message.register(self.start, Command("start"))

        # Обработчики состояний
        # self.dp.message.register(self.process_name, Form.waiting_for_name)
        # self.dp.message.register(self.process_age, Form.waiting_for_age)
        self.dp.message.register(self.server_switch, F.text == "переключить_сервер")



    async def start(self, message: Message, state: FSMContext):
        # Создаем кнопки
        kb = [
            [KeyboardButton(text="переключить_сервер")]
        ]
        keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

        await message.answer("Выберите действие:", reply_markup=keyboard)

    async def server_switch(self, message: Message, state: FSMContext):



    async def run(self):
        await self.dp.start_polling(self.bot)


def run_bot(conn: Connection = None):
    """Точка входа для multiprocessing"""
    with open('program_settings.json', 'r', encoding='utf-8') as f:
        settings = json.load(f)
    token = BOT_TOKEN or settings["telegram_bot_token"]
    bot = Bott(token, conn)

    # Настройка обработки сигналов
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(bot.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
        conn.close()

# run_bot()
#
# class Bot_dop:
#     def __init__(self, conn: Connection):
#         self.conn = conn
#         self.running = False
#         self.task = None
#
#     async def start(self):
#         """Запуск асинхронного бота"""
#         self.running = True
#         print("Bot started")
#
#
#         # Основной цикл бота
#         while self.running:
#             # Пример работы бота
#             await self.process_messages()
#             await asyncio.sleep(1)
#
#             # Проверяем сообщения из Pipe
#             if self.conn.poll():
#                 try:
#                     msg = self.conn.recv()
#                     if msg == "stop":
#                         await self.shutdown()
#                     elif isinstance(msg, tuple) and msg[0] == "command":
#                         await self.handle_command(msg[1])
#                 except EOFError:
#                     break
#
#     async def process_messages(self):
#         """Пример обработки сообщений"""
#         # Здесь ваш код бота
#         pass
#
#     async def handle_command(self, cmd):
#         """Обработка команд из главного процесса"""
#         print(f"Received command: {cmd}")
#
#     async def shutdown(self):
#         """Корректное завершение работы"""
#         self.running = False
#         print("Bot shutting down...")
#
#
# def run_bot(conn: Connection):
#     """Точка входа для multiprocessing"""
#     bot = Bot_dop(conn)
#
#     # Настройка обработки сигналов
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#
#     try:
#         loop.run_until_complete(bot.start())
#     except KeyboardInterrupt:
#         pass
#     finally:
#         loop.close()
#         conn.close()