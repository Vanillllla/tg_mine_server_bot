from aiogram import Bot, Dispatcher, types

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import subprocess
import asyncio

API_TOKEN = ''

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_action = State()

async def start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Запустить скрипт')
    await message.answer("Добро пожаловать! Выберите действие:", reply_markup=keyboard)
    await Form.waiting_for_action.set()

@dp.message_handler(lambda message: message.text == 'Запустить скрипт', state=Form.waiting_for_action)
async def process_start_script(message: types.Message, state: FSMContext):
    await message.answer('Запуск скрипта...')
    # Запуск второго скрипта как субпроцесса
    process = await asyncio.create_subprocess_exec('python', 'second_script.py')
    await message.answer('Скрипт запущен!')
    await state.finish()

dp.register_message_handler(start, commands=['start'], state='*')

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
