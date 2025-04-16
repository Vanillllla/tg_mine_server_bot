import telebot
from log_reg import log, registration
from BD_wock import add_user
from SERV_work import ServerManager

bot = telebot.TeleBot('7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg')
server = ServerManager("forge-1.12.2-14.23.5.2859.jar", cwd="Server")

def glavnay():
    @bot.message_handler(content_types=['text'])
    def worc(message):
        if str(message.text) == 'start':
            bot.send_message(message.from_user.id,
                             "Server starting...")
            print("Server starting...")
            server.start()
        elif str(message.text) == 'stop':
            bot.send_message(message.from_user.id,
                             "Server stopping...")
            print("Server stopping...")
            server.stop()

        elif str(message.text) == 'help':
            bot.send_message(message.from_user.id,
                             "Мне тоже нужна помощь\n"
                             "IP + порт : 26.50.226.151:25565\n"
                             "Minecraft_version : forge-1.12.2-14.23.5.2859.jar"
                             "Bot_version : 1.0.0 it_work\n"
                             "Петя, при первом входе на сервер, после полдключения пропиши в тг 'op' \n\n"
                             "Команды :\n"
                             "start, stop, help, op, say - писать в телеграм БЕЗ слеша\n")
            print('Мне тоже нужна помощь')
        elif str(message.text) == 'say':
            server.send_command("say Привет! Сервер работает!")
        elif str(message.text) == 'op':
            server.send_command("op T_55AMD_1")
        else:
            bot.send_message(message.from_user.id,
                             "Неизвестная команда")
            print("Неизвестная команда")




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
        glavnay()

def reg1(message):
    # print(123123123)
    if registration(message):
        bot.send_message(message.from_user.id, "Пароль верный.")
        print(message.from_user.id)
        add_user(message.from_user.id)
        bot.send_message(message.from_user.id, "Вы успешно зарегистрованный.")
        glavnay()
    else:
        bot.send_message(message.from_user.id, "Пароль НЕ верный. \nСнова введите /start")
        bot.register_next_step_handler_by_chat_id(message,start)

bot.polling(none_stop=True, interval=0)








