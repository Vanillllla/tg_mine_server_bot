import telebot
from telebot import types
from log_reg import log, registration
from BD_wock import add_user
from SERV_work import ServerManager

bot = telebot.TeleBot('7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg')
server = ServerManager("forge-1.12.2-14.23.5.2859.jar", cwd="Server")

def glavnay(message):

    user_state = {}
    STATE_MAIN_MENU = "main"
    STATE_SUBMENU = "com_menu"


    def mane_menu(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("⚙️ Запустить сервер")
        btn2 = types.KeyboardButton("⚙️ Остановить сервер")
        btn3 = types.KeyboardButton("⌨️ Режим консоли")
        btn4 = types.KeyboardButton("❓ Помощь")
        markup.add(btn1, btn2, btn3, btn4)
        bot.send_message(message.from_user.id, "Жми на кнопочки:", reply_markup=markup)

    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        state = user_state.get(message.from_user.id, STATE_MAIN_MENU)
        if state == STATE_MAIN_MENU:
            if message.text == "⚙️ Запустить сервер":
                bot.send_message(message.from_user.id,
                                 "Server starting...")
                print("Server starting...")
                server.start()
            elif message.text == "⚙️ Остановить сервер":
                bot.send_message(message.from_user.id,
                                 "Server stopping...")
                print("Server stopping...")
                server.stop()
            elif message.text == "⌨️ Режим консоли":
                com()
            elif message.text == "❓ Помощь":
                bot.send_message(message.from_user.id,
                    "Мне тоже нужна помощь\n"
                    "IP + порт : 26.50.226.151:25565\n"
                    "Minecraft_version : forge-1.12.2-14.23.5.2859.jar"
                    "Bot_version : 1.0.0 it_work\n"
                    "\n"
                    "Команды :\n"
                    "start, stop, help - писать в телеграм БЕЗ слеша\n")
                print('Мне тоже нужна помощь')
            else:
                bot.send_message(message.from_user.id, "Не понял 🤔")
        elif state == STATE_SUBMENU:
            if message.text == "🔙 Назад":
                user_state[message.from_user.id] = STATE_MAIN_MENU
                mane_menu(message)

            else:
                server.send_command(message.text)
                # bot.send_message(message.from_user.id, "Не понял 🤔")

    def com():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_back = types.KeyboardButton("🔙 Назад")
        markup.add(btn_back)
        bot.send_message(message.chat.id, "Вводите команды:", reply_markup=markup)
        user_state[message.from_user.id] = STATE_SUBMENU
        # @bot.message_handler(func=lambda message: True)
        # def nazad(message):
        #     if message.text == "🔙 Назад":
        #         glavnay()
        # @bot.message_handler(content_types=['text'])
        # def command_menu(message):
        #     server.send_command(message.text)

    mane_menu(message)




    # @bot.message_handler(content_types=['text'])
    # def worc(message):
    #     if str(message.text) == 'start':
    #         bot.send_message(message.from_user.id,
    #                          "Server starting...")
    #         print("Server starting...")
    #         server.start()
    #     elif str(message.text) == 'stop':
    #         bot.send_message(message.from_user.id,
    #                          "Server stopping...")
    #         print("Server stopping...")
    #         server.stop()

#         elif str(message.text) == 'help':
#             bot.send_message(message.from_user.id,
#                              "Мне тоже нужна помощь\n"
#                              "IP + порт : 26.50.226.151:25565\n"
#                              "Minecraft_version : forge-1.12.2-14.23.5.2859.jar"
#                              "Bot_version : 1.0.0 it_work\n"
#                              "Петя, при первом входе на сервер, после полдключения пропиши в тг 'op' \n\n"
#                              "Команды :\n"
#                              "start, stop, help - писать в телеграм БЕЗ слеша\n")
#             print('Мне тоже нужна помощь')
#         # elif str(message.text) == 'say':
#         #     server.send_command("say Привет! Сервер работает!")
#         # elif str(message.text) == 'op':
#         #     server.send_command("op T_55AMD_1")
#         # elif str(message.text) == 'op':


#         else:
#             bot.send_message(message.from_user.id,
#                              "Неизвестная команда")
#             print("Неизвестная команда: ", message.text)




@bot.message_handler(commands=['start'])
def start(message):
    print(message)
    bot.send_message(message.from_user.id,
                     "Привет, готов настроить контакт с сервером, " + str(message.from_user.username) + "?")
    if log(message):
        bot.send_message(message.from_user.id,
                         "Сначало надо зарегистривроваться.")
        bot.send_message(message.from_user.id,
                         "Введите код активации переданный вам : ")
        bot.register_next_step_handler_by_chat_id(message.from_user.id,reg1)

    else:
        bot.send_message(message.from_user.id, "Добро пожаловать " + str(message.from_user.id) + ".")
        glavnay(message)

def reg1(message):
    # print(123123123)
    if registration(message):
        bot.send_message(message.from_user.id, "Пароль верный.")
        print("Успешно заригистрирован",message.from_user.id)
        add_user(message.from_user.id)
        bot.send_message(message.from_user.id, "Вы успешно зарегистрованный.")
        glavnay(message)
    else:
        bot.send_message(message.from_user.id, "Пароль НЕ верный. \nСнова введите /start")
        bot.register_next_step_handler_by_chat_id(message,start)

bot.polling(none_stop=True, interval=0)








