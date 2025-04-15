import telebot
from log_reg import log, registration
from BD_wock import add_user

bot = telebot.TeleBot('7563076857:AAHf5MdmVCDskWN9IL1tNz4eXuwawZ0alMg')


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.from_user.id,
                     "Привет, готов настроить контакт с сервером, " + str(message.from_user.username) + "?")
    if log(message):
        bot.send_message(message.from_user.id,
                         "Сначало надо зарегистривроваться.")
        bot.send_message(message.from_user.id,
                         "Введите код активации переданный вам : ")
        bot.send_message(message.from_user.id,reg1)

    else:
        bot.send_message(message.from_user.id, "Добро пожаловать" + str(message.from_user.id) + ".")
bot.polling(none_stop=True, interval=0)


def reg1(message):
    if registration(message):
        bot.send_message(message.from_user.id, "Пароль верный.")
        add_user(message.from_user.id)
        bot.send_message(message.from_user.id, "Вы успешно зарегистрованны.")
        bot.register_next_step_handler_by_chat_id(message.from_user.id, glavnay)
    else:
        bot.send_message(message.from_user.id, "Пароль НЕ верный.")

def glavnay(message):
    print(message.text)



