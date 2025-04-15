import telebot
from log_reg import log, registration
from BD_wock import add_user

bot = telebot.TeleBot('7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg')





def glavnay(message):
    print(message.text)





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

def reg1(message):
    # print(123123123)
    if registration(message):
        bot.send_message(message.from_user.id, "Пароль верный.")
        print(message.from_user.id)
        add_user(message.from_user.id)
        bot.send_message(message.from_user.id, "Вы успешно зарегистрованный. \nСнова введите /start")
        glavnay(message)
    else:
        bot.send_message(message.from_user.id, "Пароль НЕ верный.")
        bot.register_next_step_handler_by_chat_id(message,start)

bot.polling(none_stop=True, interval=0)








