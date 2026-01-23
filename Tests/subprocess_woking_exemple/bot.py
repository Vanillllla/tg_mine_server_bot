import asyncio
import signal
import sys
from multiprocessing.connection import Connection


class Bot:
    def __init__(self, conn: Connection):
        self.conn = conn
        self.running = False
        self.task = None

    async def start(self):
        """Запуск асинхронного бота"""
        self.running = True
        print("Bot started")

        # Основной цикл бота
        while self.running:
            # Пример работы бота
            await self.process_messages()
            await asyncio.sleep(1)

            # Проверяем сообщения из Pipe
            if self.conn.poll():
                try:
                    msg = self.conn.recv()
                    if msg == "stop":
                        await self.shutdown()
                    elif isinstance(msg, tuple) and msg[0] == "command":
                        await self.handle_command(msg[1])
                except EOFError:
                    break

    async def process_messages(self):
        """Пример обработки сообщений"""
        # Здесь ваш код бота
        pass

    async def handle_command(self, cmd):
        """Обработка команд из главного процесса"""
        print(f"Received command: {cmd}")

    async def shutdown(self):
        """Корректное завершение работы"""
        self.running = False
        print("Bot shutting down...")


def run_bot(conn: Connection):
    """Точка входа для multiprocessing"""
    bot = Bot(conn)

    # Настройка обработки сигналов
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(bot.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
        conn.close()