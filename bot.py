import asyncio
import sqlite3
import requests
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage

from dotenv import load_dotenv
from aiogram import F

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

class BotStates(StatesGroup):
    """Состояния бота"""
    main_menu = State()
    profile = State()
    settings = State()


class TelegramBot:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация обработчиков"""
        self.dp.message.register(self._start_command, Command('start'))
        self.dp.message.register(self._main_menu_handler, F.text == 'Главное меню')
        self.dp.message.register(self._profile_handler, F.text == 'Профиль')
        self.dp.message.register(self._settings_handler, F.text == 'Настройки')
        self.dp.message.register(self._back_handler, F.text == 'Назад')
        self.dp.message.register(self._echo_handler)

    async def _show_menu(self, message: types.Message, state: FSMContext):
        """Показать главное меню"""
        await state.set_state(BotStates.main_menu)
        keyboard = [
            [types.KeyboardButton(text='Профиль')],
            [types.KeyboardButton(text='Настройки')]
        ]
        reply_markup = types.ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )
        await message.answer(
            'Выберите опцию:',
            reply_markup=reply_markup
        )

    async def _start_command(self, message: types.Message, state: FSMContext):
        """Обработчик команды /start"""
        await message.answer('Добро пожаловать!')
        await self._show_menu(message, state)

    async def _main_menu_handler(self, message: types.Message, state: FSMContext):
        """Главное меню"""
        await self._show_menu(message, state)

    async def _profile_handler(self, message: types.Message, state: FSMContext):
        """Обработчик профиля"""
        await state.set_state(BotStates.profile)
        keyboard = [[types.KeyboardButton(text='Назад')]]
        reply_markup = types.ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )
        await message.answer(
            'Это ваш профиль. Здесь будет информация...',
            reply_markup=reply_markup
        )

    async def _settings_handler(self, message: types.Message, state: FSMContext):
        """Обработчик настроек"""
        await state.set_state(BotStates.settings)
        keyboard = [[types.KeyboardButton(text='Назад')]]
        reply_markup = types.ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )
        await message.answer(
            'Настройки бота. Здесь будут параметры...',
            reply_markup=reply_markup
        )

    async def _back_handler(self, message: types.Message, state: FSMContext):
        """Возврат в главное меню"""
        await self._show_menu(message, state)

    async def _echo_handler(self, message: types.Message, state: FSMContext):
        """Обработчик любых сообщений"""
        current_state = await state.get_state()
        await message.answer(
            f'Состояние: {current_state}\n'
            f'Вы сказали: {message.text}'
        )

    async def run(self):
        """Запуск бота"""
        print("Бот запущен...")
        await self.dp.start_polling(self.bot)

if __name__ == '__main__':
    bot = TelegramBot(BOT_TOKEN)
    asyncio.run(bot.run())