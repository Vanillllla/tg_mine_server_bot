import asyncio
import sys
import json
import os
from typing import Dict, Any
from asyncio import Queue

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')


class BotStates(StatesGroup):
    """Состояния бота"""
    main_menu = State()
    profile = State()
    settings = State()
    console_mode = State()


class BotCommunicator:
    """Класс для общения с основным процессом"""

    def __init__(self):
        self.request_queue = Queue()  # очередь запросов
        self.response_queues: Dict[str, Queue] = {}  # очереди ответов по request_id
        self.running = True

    async def send_request(self, command: str, data: dict = None) -> dict:
        """Асинхронная отправка запроса"""
        import uuid
        request_id = str(uuid.uuid4())
        request = {
            "command": command,
            "request_id": request_id,
            "data": data or {}
        }
        # Создаем очередь для ответа
        self.response_queues[request_id] = Queue()
        # Отправляем запрос
        json_str = json.dumps(request)
        print(json_str, flush=True)
        # Ждем ответа с таймаутом
        try:
            response_queue = self.response_queues[request_id]
            response = await asyncio.wait_for(response_queue.get(), timeout=10.0)
            return response
        except asyncio.TimeoutError:
            return {"error": "Timeout waiting for response"}
        finally:
            # Удаляем очередь
            self.response_queues.pop(request_id, None)

    async def start_reader(self):
        """Запуск асинхронного чтения stdin"""
        loop = asyncio.get_event_loop()
        # Используем asyncio для неблокирующего чтения
        while self.running:
            try:
                # Читаем строку в отдельном потоке
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    await asyncio.sleep(0.1)
                    continue
                try:
                    data = json.loads(line.strip())
                    request_id = data.get("request_id")
                    # Если есть request_id, кладем в соответствующую очередь
                    if request_id and request_id in self.response_queues:
                        await self.response_queues[request_id].put(data)
                    else:
                        print(f"Неизвестный ответ: {data}", file=sys.stderr)
                except json.JSONDecodeError:
                    print(f"Неверный JSON: {line}", file=sys.stderr)
            except Exception as e:
                print(f"Ошибка чтения: {e}", file=sys.stderr)
                await asyncio.sleep(1)


class TelegramBot:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.communicator = BotCommunicator()
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация обработчиков"""
        self.dp.message.register(self._start_command, Command('start'))
        # self.dp.message.register(self._main_menu_handler, F.text == 'Главное меню')
        # self.dp.message.register(self._profile_handler, F.text == 'Профиль')
        # self.dp.message.register(self._settings_handler, F.text == 'Настройки')
        # self.dp.message.register(self._back_handler, F.text == 'Назад')
        self.dp.message.register(self._start_handler, F.text == 'Запустить сервер')
        self.dp.message.register(self._status_handler, F.text == 'Статус')
        self.dp.message.register(self._echo_handler)

    async def _show_menu(self, message: types.Message, state: FSMContext):
        """Показать главное меню"""
        await state.set_state(BotStates.main_menu)
        keyboard = [
            [types.KeyboardButton(text='Запустить сервер'), types.KeyboardButton(text='//Режим консоли')],
            [types.KeyboardButton(text='Статус'), types.KeyboardButton(text='//Настройки')]
        ]
        reply_markup = types.ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )
        await message.answer(
            'Выберите опцию:',
            reply_markup=reply_markup
        )

    async def _start_command(self, message: types.Message, state: FSMContext):
        """Обработчик команды /start"""
        await message.answer('Добро пожаловать!')
        await self._show_menu(message, state)

    async def _main_menu_handler(self, message: types.Message, state: FSMContext):
        """Главное меню"""
        await self._show_menu(message, state)

    async def _profile_handler(self, message: types.Message, state: FSMContext):
        """Обработчик профиля"""
        await state.set_state(BotStates.profile)
        keyboard = [[types.KeyboardButton(text='Назад')]]
        reply_markup = types.ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )
        await message.answer(
            'Это ваш профиль. Здесь будет информация...',
            reply_markup=reply_markup
        )

    async def _back_handler(self, message: types.Message, state: FSMContext):
        """Возврат в главное меню"""
        await self._show_menu(message, state)

    async def _start_handler(self, message: types.Message, state: FSMContext):
        try:
            response = await self.communicator.send_request("switch_server", data={})

            if response.get("error"):
                await message.answer(f"Ошибка: {response['error']}")
            else:
                status = response.get("status", False)
                await message.answer(f"Статус сервера: {'Запущен' if status else 'Остановлен'}")
        except Exception as e:
            await message.answer(f"Ошибка при запросе статуса: {e}")

    async def _status_handler(self, message: types.Message, state: FSMContext):
        """Обработчик кнопки 'Запустить сервер'"""
        try:
            # Отправляем запрос асинхронно
            response = await self.communicator.send_request("get_status")

            if response.get("error"):
                await message.answer(f"Ошибка: {response['error']}")
            else:
                status = response.get("status", False)
                await message.answer(f"Статус сервера: {'Запущен' if status else 'Остановлен'}")
        except Exception as e:
            await message.answer(f"Ошибка при запросе статуса: {e}")

    async def _echo_handler(self, message: types.Message, state: FSMContext):
        """Обработчик любых сообщений"""
        current_state = await state.get_state()
        await message.answer(
            f'Состояние: {current_state}\n'
            f'Вы сказали: {message.text}'
        )

    async def run(self):
        """Запуск бота"""
        print("Бот запускается...", file=sys.stderr)

        # Запускаем чтение stdin в фоне
        reader_task = asyncio.create_task(self.communicator.start_reader())

        try:
            print("Бот запущен!", file=sys.stderr)
            await self.dp.start_polling(self.bot)
        finally:
            self.communicator.running = False
            await reader_task


async def main():
    bot = TelegramBot(BOT_TOKEN)
    await bot.run()


if __name__ == '__main__':
    asyncio.run(main())