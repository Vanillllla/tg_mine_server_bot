import asyncio
import sqlite3
import os
from ipaddress import ip_address

import psutil
import pynvml
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from SERV_work import ServerManager

from dotenv import load_dotenv
load_dotenv()


# Инициализация бота и диспетчера
bot = Bot(token="7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg")
dp = Dispatcher()

# Инициализация сервера
server = ServerManager("forge-1.12.2-14.23.5.2859.jar", cwd="Server")


# Состояния бота
class Form(StatesGroup):
    main_menu = State()
    console_mode = State()
    registration = State()
    more_mode = State()
    setings = State()

# --- Вспомогательные функции базы данных ---
def in_bd(user_id):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()
    cursor.execute('SELECT users_tg_id FROM Users WHERE users_tg_id = ?', (user_id,))
    results = cursor.fetchall()
    if results:
        connection.close()
        return True
    else:
        connection.close()
        return False


def add_user(user_id):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()
    cursor.execute('INSERT INTO Users (users_tg_id) VALUES (?)', (str(user_id),))
    connection.commit()
    connection.close()


def check_password(input_password: str) -> bool:
    correct_password = os.getenv('REGISTRATION_PASSWORD')
    return input_password == correct_password


# --- Клавиатуры ---
def get_main_keyboard(is_server_running: bool):
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="⚙️ Остановить сервер" if is_server_running else "⚙️ Запустить сервер"),
                KeyboardButton(text="🧪 Режим консоли")
            ],
            [
                KeyboardButton(text="🚀 Быстрые команды"),
                KeyboardButton(text="🛠️ Настройки"),
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True
    )
    return markup


def get_more_keyboard():
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔙 Назад")
            ],
            [
                KeyboardButton(text="Установить день"),
                KeyboardButton(text="Ясная погода"),
                KeyboardButton(text="Узнать онлайн")
            ],
            [
                KeyboardButton(text="Харакири"),
                KeyboardButton(text="Очистить мир"),
                KeyboardButton(text="Получить администратора")
            ],
            [

            ]
        ],
        resize_keyboard=True
    )
    return markup

def get_setings_keyboard():
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔙 Назад"), KeyboardButton(text="📊 Показать статус")
            ],
            [
                KeyboardButton(text="/start")
            ]
        ],
        resize_keyboard=True
    )
    return markup

def get_console_keyboard():
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="/start")]
        ],
        resize_keyboard=True
    )
    return markup


# --- Обработчики команд ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if in_bd(message.from_user.id):
        await message.answer(f"Добро пожаловать, {message.from_user.username}!")
        await show_main_menu(message, state)
    else:
        await message.answer(f"Привет, {message.from_user.username}! Необходимо зарегистрироваться.")
        await message.answer("Введите код активации переданный вам:")
        await state.set_state(Form.registration)


@dp.message(Command("set_password"))
async def set_password(message: types.Message):


    conn = sqlite3.connect('my_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM Users WHERE users_tg_id = ?", (f"{message.from_user.id}",))
    result = cursor.fetchone()
    conn.close()
    if str(result[0]) != "1":
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /set_password <новый_пароль>")
        return

    new_password = args[1]

    # Обновляем .env файл
    with open(".env", "r") as f:
        lines = f.readlines()

    with open(".env", "w") as f:
        for line in lines:
            if line.startswith("REGISTRATION_PASSWORD="):
                f.write(f"REGISTRATION_PASSWORD={new_password}\n")
            else:
                f.write(line)

    await message.answer("✅ Пароль успешно изменен!")


@dp.message(Form.registration)
async def process_registration(message: types.Message, state: FSMContext):
    if check_password(message.text):
        add_user(message.from_user.id)
        await message.answer("Вы успешно зарегистрированы!")
        await show_main_menu(message, state)
    else:
        await message.answer("Пароль неверный. Повторите /start.")
        await state.clear()


# --- Основные обработчики ---
async def show_main_menu(message: types.Message, state: FSMContext):
    is_running = server.process and server.process.poll() is None
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard(is_running)
    )
    await state.set_state(Form.main_menu)


@dp.message(Form.main_menu)
async def handle_main_menu(message: types.Message, state: FSMContext):
    is_running = server.process and server.process.poll() is None

    if message.text == "⚙️ Запустить сервер" and not is_running:
        await message.answer("⏳ Ожидание запуска сервера...")
        response = await asyncio.to_thread(server.start)
        await message.answer(response)
        await show_main_menu(message, state)

    elif message.text == "⚙️ Запустить сервер" and is_running:
        await message.answer("ERROR - Вы отстали от всех, консоль обновлена!")
        await show_main_menu(message, state)

    elif message.text == "⚙️ Остановить сервер" and is_running:
        await message.answer("🛑 Останавливаем сервер...")
        response = await asyncio.to_thread(server.stop)
        await message.answer(response)
        await show_main_menu(message, state)

    elif message.text == "⚙️ Остановить сервер" and not is_running:
        await message.answer("ERROR - Вы отстали от всех, консоль обновлена!")
        await show_main_menu(message, state)

    elif message.text == "🧪 Режим консоли":
        await message.answer(
            "Команды для майнкрафт консоли : <a href='https://timeweb.com/ru/community/articles/komandy-dlya-servera-minecraft'>ТЫК</a>\n"
            "Вводите команды:",
            reply_markup=get_console_keyboard()
        )
        await state.set_state(Form.console_mode)

    elif message.text == "🚀 Быстрые команды":
        await message.answer(
            "Ура! Ты открыл новые функции:",
            reply_markup=get_more_keyboard()
        )
        await state.set_state(Form.more_mode)

    elif message.text == "📊 Показать статус":
        await send_server_status(message)

    elif message.text == "❓ Помощь":
        with open('Server/server.properties', 'r') as file:
            for i, line in enumerate(file, 1):
                if i == 24:
                    ip_today = line.strip()[10::]
                    break
        await message.answer(
            "Minecraft_version : forge-1.12.2-14.23.5.2859.jar\n"
            f"IP + порт : <code>{ip_today}:25565</code>\n\n"
            "Сеть <a href='https://www.radmin-vpn.com/ru/'>RadminVPN</a> : \n"
            "  login: <code>12345678900000000000</code>\n"
            "  password: <code>123456</code>\n\n"
            f"Пароль для регистрации в боте: <code>{os.getenv('REGISTRATION_PASSWORD')}</code>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    else:
        await message.answer("Не понял 🤔")

@dp.message(Form.more_mode)
async def handle_more_mode(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await show_main_menu(message, state)

    elif message.text == "Получить администратора":
        conn = sqlite3.connect('my_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT Game_name FROM users WHERE users_tg_id = ?", (f"{message.from_user.id}",))
        result = cursor.fetchone()
        conn.close()
        if result[0] == None:
            await message.answer("ERROR - Не указан никнейм в игре, посетите меню настройки!")
        else:
            response = await asyncio.to_thread(server.send_command, f"/op {result[0]}")
            await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Установить день":
        response = await asyncio.to_thread(server.send_command, f"/time set day")
        await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Ясная погода":
        response = await asyncio.to_thread(server.send_command, f"/time set day")
        await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Узнать онлайн":
        response = await asyncio.to_thread(server.send_command, f"/list")
        await asyncio.to_thread(server.send_command, f"/say Кто-то чекнул онлан )")
        await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Харакири":
        conn = sqlite3.connect('my_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT Game_name FROM users WHERE users_tg_id = ?", (f"{message.from_user.id}",))
        result = cursor.fetchone()
        conn.close()
        if result[0] == None:
            await message.answer("ERROR - Не указан никнейм в игре, посетите меню настройки!")
        else:
            response = await asyncio.to_thread(server.send_command, f"/kill {result[0]}")
            await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Очистить мир":
        response = await asyncio.to_thread(server.send_command, f"/kill @e[type=item]")
        await message.answer(f"📨 Ответ сервера: \n{response}")

    else:
        await message.answer("неВОРКАЕТ!!!")


@dp.message(Form.console_mode)
async def handle_console_mode(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await show_main_menu(message, state)
    else:
        # await message.answer("ВОРКАЕТ!!!")
        response = await asyncio.to_thread(server.send_command, message.text)
        await message.answer(f"📨 Ответ сервера: \n{response}")


# --- Функция статуса сервера ---
async def send_server_status(message: types.Message):
    # Статус сервера
    if server.process and server.process.poll() is None:
        server_status = "✅ Сервер сейчас работает."
    else:
        server_status = "❌ Сервер выключен."

    # Загрузка CPU
    cpu_load = psutil.cpu_percent(interval=1)

    # Загрузка RAM
    virtual_memory = psutil.virtual_memory()
    ram_used_gb = virtual_memory.used / (1024 ** 3)
    ram_total_gb = virtual_memory.total / (1024 ** 3)
    ram_percent = virtual_memory.percent

    # Загрузка GPU
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpu_load = gpu_util.gpu
        gpu_used_gb = gpu_memory.used / (1024 ** 3)
        gpu_total_gb = gpu_memory.total / (1024 ** 3)
        pynvml.nvmlShutdown()
        gpu_info = (f"🎮 GPU загрузка: {gpu_load}%\n"
                    f"🎮 GPU память: {gpu_used_gb:.2f}ГБ / {gpu_total_gb:.2f}ГБ")
    except Exception as e:
        gpu_info = "🎮 GPU: Недоступно"

    response = (
        f"{server_status}\n\n"
        f"🧠 CPU загрузка: {cpu_load}%\n"
        f"💾 RAM: {ram_used_gb:.2f}ГБ / {ram_total_gb:.2f}ГБ ({ram_percent}%)\n"
        f"{gpu_info}"
    )
    await message.answer(response)


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())