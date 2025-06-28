from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = Bot(token="YOUR_BOT_TOKEN")
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(row_width=2)  # row_width - кол-во кнопок в строке
    buttons = [
        InlineKeyboardButton("Кнопка 1", callback_data="btn1"),
        InlineKeyboardButton("Кнопка 2", callback_data="btn2"),
        InlineKeyboardButton("Google", url="https://google.com"),
    ]
    keyboard.add(*buttons)  # Добавляем кнопки в клавиатуру

    await message.answer("Привет! Выбери действие:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "btn1")
async def process_callback_btn1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Ты нажал Кнопку 1!")

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp)