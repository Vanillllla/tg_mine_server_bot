import telebot
import multiprocessing as mp
from log_reg import log, registration
from BD_wock import add_user
from SERV_work import serv_start

bot = telebot.TeleBot('7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg')

def glavnay():
    @bot.message_handler(content_types=['text'])
    def worc(message):
        if str(message.text) == 'start':
            bot.send_message(message.from_user.id,
                             "Server starting...")
            print("Server starting...")
            serv_start()


        elif str(message.text) == 'help':
            bot.send_message(message.from_user.id,
                             "Мне тоже нужна помощь")
            print('Мне тоже нужна помощь')
        else:
            bot.send_message(message.from_user.id,
                             "Неизвестная команда")
            print("Неизвестная команда")

    bot.polling(none_stop=True, interval=0)


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








