from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = Bot(token="YOUR_BOT_TOKEN")
dp = Dispatcher()

# Клавиатура с кнопками
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Кнопка 1", callback_data="btn1")],
        [InlineKeyboardButton(text="Google", url="https://google.com")]
    ])
    await message.answer("Выберите действие:", reply_markup=keyboard)

# Обработка нажатия на кнопку (вариант 1 — через Text("btn1"))
@dp.callback_query(Text("btn1"))  # Фильтр Text("btn1") вместо lambda
async def handle_btn1(callback: types.CallbackQuery):
    await callback.answer("Вы нажали Кнопку 1!", show_alert=True)
    await callback.message.edit_text("✅ Кнопка 1 нажата!")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())