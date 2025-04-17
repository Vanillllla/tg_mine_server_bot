# import telebot
# from telebot import types
#
# bot = telebot.TeleBot('7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg')
#
# @bot.message_handler(commands=['start'])
# def start(message):
#     main_menu(message)
#
# # Основное меню
# def main_menu(message):
#     markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
#     btn1 = types.KeyboardButton("📂 Подменю")
#     btn2 = types.KeyboardButton("❓ Помощь")
#     markup.add(btn1, btn2)
#     bot.send_message(message.chat.id, "Выбери пункт меню:", reply_markup=markup)
#
# # Обработка нажатий
# @bot.message_handler(func=lambda message: True)
# def handle_message(message):
#     if message.text == "📂 Подменю":
#         submenu(message)
#     elif message.text == "🔙 Назад":
#         main_menu(message)
#     elif message.text == "❓ Помощь":
#         bot.send_message(message.chat.id, "Это просто тестовое меню.")
#     elif message.text == "🧪 Кнопка A":
#         bot.send_message(message.chat.id, "Ты нажал кнопку A!")
#     elif message.text == "⚙️ Кнопка B":
#         bot.send_message(message.chat.id, "Ты нажал кнопку B!")
#     else:
#         bot.send_message(message.chat.id, "Не понял 🤔")
#
# # Подменю
# def submenu(message):
#     markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
#     btn1 = types.KeyboardButton("🧪 Кнопка A")
#     btn2 = types.KeyboardButton("⚙️ Кнопка B")
#     btn_back = types.KeyboardButton("🔙 Назад")
#     markup.add(btn1, btn2)
#     markup.add(btn_back)
#     bot.send_message(message.chat.id, "Это подменю. Выбери действие:", reply_markup=markup)
#
# bot.polling(none_stop=True, interval=0)
#


import telebot
from telebot import types

bot = telebot.TeleBot("7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg")

# Хранилище состояний пользователей
user_state = {}

STATE_MAIN_MENU = "main"
STATE_SUBMENU = "submenu"


@bot.message_handler(commands=['start'])
def start(message):
    user_state[message.chat.id] = STATE_MAIN_MENU
    main_menu(message)


# Главное меню
def main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📂 Подменю"), types.KeyboardButton("❓ Помощь"))
    bot.send_message(message.chat.id, "Главное меню. Выбери действие:", reply_markup=markup)


# Подменю
def submenu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🧪 Кнопка A"), types.KeyboardButton("⚙️ Кнопка B"))
    markup.add(types.KeyboardButton("🔙 Назад"))
    bot.send_message(message.chat.id, "submenu", reply_markup=markup)

    # Устанавливаем состояние
    user_state[message.from_user.id] = STATE_SUBMENU


# Обработка всех текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    state = user_state.get(message.chat.id, STATE_MAIN_MENU)

    if state == STATE_MAIN_MENU:
        # Принимаем только кнопки в главном меню
        if message.text == "📂 Подменю":
            submenu(message)
        elif message.text == "❓ Помощь":
            bot.send_message(message.chat.id, "Это помощь по боту.")
        else:
            bot.send_message(message.chat.id, "В главном меню нельзя писать текстовые сообщения.")

    elif state == STATE_SUBMENU:
        if message.text == "🔙 Назад":
            user_state[message.chat.id] = STATE_MAIN_MENU
            main_menu(message)
        elif message.text == "🧪 Кнопка A":
            bot.send_message(message.chat.id, "Ты нажал A!")
        elif message.text == "⚙️ Кнопка B":
            bot.send_message(message.chat.id, "Ты нажал B!")
        else:
            bot.send_message(message.chat.id, f"Ты написал: {message.text}")


bot.polling(none_stop=True, interval=0)