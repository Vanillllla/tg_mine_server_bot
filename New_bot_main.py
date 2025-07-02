import asyncio
import sqlite3
import os

import requests

import psutil
import pynvml
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from SERV_work import ServerManager

# Подгрузка паролей и т. п.
from dotenv import load_dotenv
load_dotenv()

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

# Инициализация сервера
# forge-1.12.2-14.23.5.2859.jar
# Magma-1.12.2-b4c01d2-server.jar
server = ServerManager("Magma-1.12.2-b4c01d2-server.jar", cwd="Server")
mods_folder = "Server/mods"
plugins_folder = "Server/plugins"
owner = "Vanillllla"       # Владелец репозитория
repo = "tg_mine_server_bot"
branch = "master"

# Состояния бота
class Form(StatesGroup):
    main_menu = State()
    console_mode = State()
    registration = State()
    more_mode = State()
    settings_mode = State()
    settings_nane_mode = State()


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


def get_latest_release():
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
    headers = {}
    if "GITHUB_TOKEN" in os.environ:
        headers["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"
        # print(headers)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Проверяем на ошибки HTTP

        commit_data = response.json()
        # print(commit_data,"\n\n",commit_data['commit']['message'])
        return commit_data['commit']['message']

    except requests.exceptions.RequestException as e:
        # print(f"Ошибка при получении коммита: {e}")
        return os.getenv('PROGRAM_VERSION')


async def update_notification():
    user_ids = []
    version = get_latest_release()

    try:
        conn = sqlite3.connect('my_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT users_tg_id FROM Users WHERE UpDate_flag = 1")
        rows = cursor.fetchall()
        user_ids = [row[0] for row in rows]
        conn.close()
    except sqlite3.Error as e:
        print(f"Ошибка при работе с SQLite: {e}")

    try:
        for i in range(len(user_ids)):
            await bot.send_message(chat_id=user_ids[i], text=f"Бот обновлён до версии: {version}\n\n"
                                                             "Если бот не запускается, введите /start", parse_mode='HTML')
    except:
        print("⚠️ Error start message!")


def add_user(user_id):
    connection = sqlite3.connect('my_database.db')
    cursor = connection.cursor()
    cursor.execute('INSERT INTO Users (users_tg_id) VALUES (?)', (str(user_id),))
    connection.commit()
    connection.close()


def check_password(input_password: str) -> bool:
    load_dotenv('.env', override=True)
    correct_password = os.getenv('REGISTRATION_PASSWORD')
    # print(123123)
    return input_password == correct_password


def have_name(message):
    conn = sqlite3.connect('my_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT Game_name FROM users WHERE users_tg_id = ?", (f"{message.from_user.id}",))
    result = cursor.fetchone()
    conn.close()
    return result


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


def get_setings_keyboard(subscript):
    # print(subscript)
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔙 Назад")
            ],
            [
                KeyboardButton(text="📊 Показать статус"),KeyboardButton(text="🟢 Уведомления о обновлении" if subscript else "🔴 Уведомления о обновлении")
            ],
            [
                KeyboardButton(text="👨🏻‍💻 Прикрепить игровой никнейм"),
            ]
        ],
        resize_keyboard=True
    )
    return markup


def get_console_keyboard():
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    return markup


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
        await message.answer("⚠️ ERROR - Вы отстали от всех, консоль обновлена!")
        await show_main_menu(message, state)

    elif message.text == "⚙️ Остановить сервер" and is_running:
        await message.answer("🛑 Останавливаем сервер...")
        response = await asyncio.to_thread(server.stop)
        await message.answer(response)
        await show_main_menu(message, state)

    elif message.text == "⚙️ Остановить сервер" and not is_running:
        await message.answer("⚠️ ERROR - Вы отстали от всех, консоль обновлена!")
        await show_main_menu(message, state)

    elif message.text == "🧪 Режим консоли":
        await message.answer(
            "Команды для майнкрафт консоли : <a href='https://timeweb.com/ru/community/articles/komandy-dlya-servera-minecraft'>ТЫК</a>\n"
            "Вводите команды:",
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=get_console_keyboard()
        )
        await state.set_state(Form.console_mode)

    elif message.text == "🚀 Быстрые команды":
        await message.answer(
            "Ура! Ты открыл быстрые команды:",
            reply_markup=get_more_keyboard()
        )
        await state.set_state(Form.more_mode)

    elif message.text == "🛠️ Настройки":
        connection = sqlite3.connect('my_database.db')
        cursor = connection.cursor()
        cursor.execute('SELECT UpDate_flag FROM Users WHERE users_tg_id = ?', (message.from_user.id,))
        results = cursor.fetchall()
        # print(results[0][0])
        if results[0][0] == 1:
            connection.close()
            subscript = True
        else:
            connection.close()
            subscript = False

        await message.answer(
            "Ура! Ты открыл настройки:",
            reply_markup=get_setings_keyboard(subscript)
        )
        await state.set_state(Form.settings_mode)


    elif message.text == "❓ Помощь":
        load_dotenv('.env', override=True)

        # with open('Server/server.properties', 'r') as file:
        #     for i, line in enumerate(file, 1):
        #         if i == 24:
        #             ip_today = line.strip()[10::]
        #             break

        keyboard_help = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Моды", callback_data="btn1"),
                InlineKeyboardButton(text="Плагины", callback_data="btn2")]
            ])


        await message.answer(
            "Minecraft_version : forge-1.12.2-14.23.5.2859.jar\n"
            f"IP + порт : <code>{os.getenv('IP_TODAY')}</code>\n\n"
            f"Скачать сборку: <a href='https://disk.yandex.ru/d/aaypyQB7Dt7yEg'>ТЫК</a>\n"
            f"Скачать ресурспак: <a href='https://www.dropbox.com/scl/fi/e2emccm0twy10w8klhm1m/MVP-IR-1.8-mc1.12.2-by-FrozeRain.zip?rlkey=hjtqqmz6nfn49avkccecl4360&e=5&st=dmp20ru9&dl=1'>ТЫК</a>\n\n"
            # "Сеть <a href='https://www.radmin-vpn.com/ru/'>RadminVPN</a> : \n"
            # "  login: <code>1234567890000000000</code>\n"
            # "  password: <code>123456</code>\n\n"
            f"Пароль для регистрации в боте: <code>{os.getenv('REGISTRATION_PASSWORD')}</code>",
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=keyboard_help
        )
    else:
        await message.answer("Не понял 🤔")

@dp.callback_query(Form.main_menu)
async def buttons_help(callback: types.CallbackQuery):
    if callback.data == "btn1":
        try:

            out_put = os.listdir(mods_folder)

            exclude_list = ["1.12.2", "memory_repo"]
            exclude_set = set(exclude_list)

            mods_text = "\n".join(
                f"{i + 1}. {mod}"
                for i, mod in enumerate(mod for mod in out_put if mod not in exclude_set)
            )
            print(mods_text)
            await callback.message.answer(f"<b>Список модов:</b>\n{mods_text}", parse_mode='HTML')

        except FileNotFoundError:
            error_msg = f"Ошибка: папка {mods_folder} не найдена"
            print(error_msg)
            await callback.message.answer(error_msg)
        except PermissionError:
            error_msg = f"Ошибка: нет доступа к папке {mods_folder}"
            print(error_msg)
            await callback.message.answer(error_msg)
        except Exception as e:
            error_msg = f"Произошла ошибка: {e}"
            print(error_msg)
            await callback.message.answer(error_msg)
    elif callback.data == "btn2":
        try:

            out_put = [f for f in os.listdir(plugins_folder) if os.path.isfile(os.path.join(plugins_folder, f))]

            exclude_list = []
            exclude_set = set(exclude_list)

            mods_text = "\n".join(
                f"{i + 1}. {mod}"
                for i, mod in enumerate(mod for mod in out_put if mod not in exclude_set)
            )

            await callback.message.answer(f"<b>Список плагинов:</b>\n{mods_text}", parse_mode='HTML')

        except FileNotFoundError:
            error_msg = f"Ошибка: папка {plugins_folder} не найдена"
            print(error_msg)
            await callback.message.answer(error_msg)
        except PermissionError:
            error_msg = f"Ошибка: нет доступа к папке {plugins_folder}"
            print(error_msg)
            await callback.message.answer(error_msg)
        except Exception as e:
            error_msg = f"Произошла ошибка: {e}"
            print(error_msg)
            await callback.message.answer(error_msg)
    await callback.answer()  # Закрыть "часики"


@dp.message(Form.more_mode)
async def handle_more_mode(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await show_main_menu(message, state)

    elif message.text == "Получить администратора":
        result = have_name(message)
        if result[0] == None:
            await message.answer("⚠️ ERROR - Не указан игровой никнейм, посетите меню настройки!")
        else:
            response = await asyncio.to_thread(server.send_command, f"op {result[0]}")
            await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Установить день":
        response = await asyncio.to_thread(server.send_command, f"time set day")
        await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Ясная погода":
        response = await asyncio.to_thread(server.send_command, f"weather clear")
        await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Узнать онлайн":
        response = await asyncio.to_thread(server.send_command, f"list")
        await asyncio.to_thread(server.send_command, f"say Кто-то чекнул онлан )")
        await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Харакири":
        result = have_name(message)
        if result[0] == None:
            await message.answer("⚠️ ERROR - Не указан игровой никнейм, посетите меню настройки!")
        else:
            response = await asyncio.to_thread(server.send_command, f"kill {result[0]}")
            await message.answer(f"📨 Ответ сервера: \n{response}")

    elif message.text == "Очистить мир":
        response = await asyncio.to_thread(server.send_command, f"kill @e[type=item]")
        await message.answer(f"📨 Ответ сервера: \n{response}")

    else:
        await message.answer("неВОРКАЕТ!!!")


@dp.message(Form.settings_mode)
async def handle_settings_mode(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await show_main_menu(message, state)

    elif message.text == "📊 Показать статус":
        await send_server_status(message)

    elif message.text == "🟢 Уведомления о обновлении":
        try:
            connection = sqlite3.connect('my_database.db')
            cursor = connection.cursor()
            cursor.execute('UPDATE Users SET UpDate_flag = ? WHERE users_tg_id = ?', (str(0), str(message.from_user.id)))
            connection.commit()
            connection.close()
            subscript = False
            await message.answer("Уведомления отключены",reply_markup = get_setings_keyboard(subscript))
        except:
            await message.answer("⚠️ ERROR - Ошибка при обращении к БД")

    elif message.text == "🔴 Уведомления о обновлении":
        try:
            connection = sqlite3.connect('my_database.db')
            cursor = connection.cursor()
            cursor.execute('UPDATE Users SET UpDate_flag = ? WHERE users_tg_id = ?', (str(1), str(message.from_user.id)))
            connection.commit()
            connection.close()
            subscript = True
            await message.answer("Уведомления включены",reply_markup = get_setings_keyboard(subscript))

        except:
            await message.answer("⚠️ ERROR - Ошибка при обращении к БД")

    elif message.text == "👨🏻‍💻 Прикрепить игровой никнейм":
        await message.answer("Введите игровой никнейм, если никнейм уже привязан, то он будет заменён:\n"
                             "Для отмены напиши: '.' ")
        await state.set_state(Form.settings_nane_mode)
        # result = have_name(message)
        # if result[0] == None:


@dp.message(Form.settings_nane_mode)
async def handle_settings_nane_mode(message: types.Message, state: FSMContext):
    if message.text == ".":
        await state.set_state(Form.settings_mode)
    else:
        try:
            connection = sqlite3.connect('my_database.db')
            cursor = connection.cursor()
            cursor.execute('UPDATE Users SET Game_name = ? WHERE users_tg_id = ?', (str(message.text), str(message.from_user.id)))
            connection.commit()
            connection.close()
            await message.answer("Новый никнейм сохранён")
        except:
            await message.answer("⚠️ ERROR - Ошибка при обращении к БД")
        finally:
            await state.set_state(Form.settings_mode)


@dp.message(Form.console_mode)
async def handle_console_mode(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await show_main_menu(message, state)
    else:
        # await message.answer("ВОРКАЕТ!!!")
        response = await asyncio.to_thread(server.send_command, message.text)
        await message.answer(f"📨 Ответ сервера: \n{response}")


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
    await update_notification()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())