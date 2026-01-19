# bot = telebot.TeleBot('7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg')
import telebot
from telebot import types

from BD_wock import add_user, in_bd
from Arhive_V2.SERV_work import ServerManager
import psutil
import pynvml


bot = telebot.TeleBot('7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg')
server = ServerManager("forge-1.12.2-14.23.5.2859.jar", cwd="Server")

user_state = {}
STATE_MAIN_MENU = "main"
STATE_SUBMENU = "com_menu"

# --- Вспомогательные функции авторизации ---

def is_registered(user_id):
    return in_bd(user_id)

def check_password(password):
    return password == "Go_V_Maincraft"

# --- Регистрация и логин ---

def start_registration(message):
    bot.send_message(message.chat.id, "Введите код активации переданный вам : ")
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_registration)

def handle_registration(message):
    if check_password(message.text):
        add_user(message.from_user.id)
        bot.send_message(message.chat.id, "Вы успешно зарегистрированы!")
        print("Зарегестрирован ", message.from_user.id)
        show_main_menu(message)
    else:
        bot.send_message(message.chat.id, "Пароль неверный. Повторите /start.")

# --- Главное меню ---

def show_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if server.process and server.process.poll() is None:
        markup.add(
            types.KeyboardButton("⚙️ Остановить сервер"),
            types.KeyboardButton("🧪 Режим консоли"),
            types.KeyboardButton("📊 Показать статус"),
            types.KeyboardButton("❓ Помощь")
        )
    else:
        markup.add(
            types.KeyboardButton("⚙️ Запустить сервер"),
            types.KeyboardButton("🧪 Режим консоли"),
            types.KeyboardButton("📊 Показать статус"),
            types.KeyboardButton("❓ Помощь")
        )
    # bot.send_message(message.chat.id, "Жми на кнопочки:", reply_markup=markup)
    user_state[message.chat.id] = STATE_MAIN_MENU

def show_console_mode(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Назад"))
    bot.send_message(message.chat.id, "Вводите команды:", reply_markup=markup)
    user_state[message.chat.id] = STATE_SUBMENU

# --- Отображение статуса сервера и пк ---

def send_server_status(message):
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
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Первая видеокарта
        gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpu_load = gpu_util.gpu  # в процентах
        gpu_used_gb = gpu_memory.used / (1024 ** 3)
        gpu_total_gb = gpu_memory.total / (1024 ** 3)
        pynvml.nvmlShutdown()
        gpu_info = (f"🎮 GPU загрузка: {gpu_load}%\n"
                    f"🎮 GPU память: {gpu_used_gb:.2f}ГБ / {gpu_total_gb:.2f}ГБ")
    except Exception as e:
        gpu_info = "🎮 GPU: Недоступно"

    # Формируем ответ
    response = (
        f"{server_status}\n\n"
        f"🧠 CPU загрузка: {cpu_load}%\n"
        f"💾 RAM: {ram_used_gb:.2f}ГБ / {ram_total_gb:.2f}ГБ ({ram_percent}%)\n"
        f"{gpu_info}"
    )
    print(response)
    bot.send_message(message.chat.id, response)




# --- Обработчики сообщений ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    if is_registered(message.from_user.id):
        bot.send_message(message.chat.id, f"Добро пожаловать, {message.chat.username}!")
        print("Вошёл ", message.chat.username, ' ' + str(message.from_user.id))

        show_main_menu(message)
    else:
        bot.send_message(message.chat.id, f"Привет, {message.chat.username}! Необходимо зарегистрироваться.")
        start_registration(message)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not is_registered(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ Вы не зарегистрированы. Введите /start")
        return

    state = user_state.get(message.chat.id, STATE_MAIN_MENU)

    if state == STATE_MAIN_MENU:
        if message.text == "⚙️ Запустить сервер":
            bot.send_message(message.chat.id,"⏳ Ожидание запуска сервера...")
            print("⏳ Ожидание запуска сервера...")
            sand = server.start()
            print(sand)
            bot.send_message(message.chat.id, sand)
            show_main_menu(message)
        elif message.text == "⚙️ Остановить сервер":
            bot.send_message(message.chat.id, "🛑 Останавливаем сервер...")
            sand = server.stop()
            print(sand)
            bot.send_message(message.chat.id, sand)
            show_main_menu(message)
        elif message.text == "🧪 Режим консоли":
            print("🧪 Режим консоли")
            show_console_mode(message)
        elif message.text == "📊 Показать статус":
            print("📊 Показать статус")
            send_server_status(message)
        elif message.text == "❓ Помощь":
            print('❓Мне тоже нужна помощь!❓')
            bot.send_message(message.chat.id,
                             "Minecraft_version : forge-1.12.2-14.23.5.2859.jar\n"
                             "IP + порт : <code>26.50.226.151:25565</code>\n\n"
                             "Сеть RadminVPN : \n"
                             "  login: <code>''.join(str(i) for i in range(1,10))+'0'*10</code>\n"
                             "  password: <code>123456</code>\n\n"
                             "Команды для майнкрафт консоли : <a href='https://timeweb.com/ru/community/articles/komandy-dlya-servera-minecraft'>ТЫК</a>\n"
                             "P. S. Чтобы выдать админку: <code>op</code> <b>ник</b>",
                             parse_mode='HTML',
                             disable_web_page_preview=True)
        else:
            bot.send_message(message.chat.id, "Не понял 🤔")
    elif state == STATE_SUBMENU:
        if message.text == "🔙 Назад":
            show_main_menu(message)
        else:
            bot.send_message(message.chat.id, "📨 Ответ сервера: \n" + server.send_command(message.text))

# --- Запуск бота ---
bot.polling(none_stop=True)


