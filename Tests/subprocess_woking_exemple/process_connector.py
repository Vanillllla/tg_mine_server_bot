from multiprocessing import Process, Pipe
import time
import sys


def start_bot():
    """Запуск бота в отдельном процессе"""
    parent_conn, child_conn = Pipe()
    p = Process(target=run_bot_process, args=(child_conn,))
    p.start()
    return p, parent_conn


def run_bot_process(conn):
    """Запускает файл bot.py в дочернем процессе"""
    sys.path.insert(0, '.')
    from bot import run_bot
    run_bot(conn)


if __name__ == '__main__':
    # Запуск бота
    print("Starting bot...")
    bot_process, bot_conn = start_bot()

    # Ждем немного
    time.sleep(3)

    # Отправляем команду боту
    print("Sending command to bot...")
    bot_conn.send(("command", "update_settings"))

    # Ждем еще
    time.sleep(2)

    # Останавливаем бота
    print("Stopping bot...")
    bot_conn.send("stop")

    # Ждем завершения
    bot_process.join(timeout=5)
    if bot_process.is_alive():
        bot_process.terminate()
        bot_process.join()

    print("Bot stopped")
    bot_conn.close()












































# import subprocess
# import sys
# import threading
# import json
# import time
# import queue
#
#
# class ProcessConnector:
#     def __init__(self):
#         self.process = None
#         self.response_queue = queue.Queue()  # очередь ответов для бота
#         self.status = False
#         self.running = False
#         print("ProcessConnector is initialized")
#
#     def bot_start(self):
#         if self.process:
#             print("Бот уже запущен")
#             return
#         try:
#             self.process = subprocess.Popen(
#                 [sys.executable, "bot.py"],
#                 stdin=subprocess.PIPE,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 text=True,
#                 bufsize=1,
#                 universal_newlines=True
#             )
#             self.running = True
#
#             threading.Thread(target=self._read_from_bot, daemon=True).start()
#             threading.Thread(target=self._write_to_bot, daemon=True).start()
#             # threading.Thread(target=self._read_bot_stderr, daemon=True).start()
#             print("Бот успешно запущен")
#
#         except Exception as e:
#             print(f"Ошибка запуска бота: {e}")
#             self.running = False
#
#     def _read_from_bot(self):
#         while True:
#             try:
#                 line = self.process.stdout.readline()
#                 print(line)
#             except Exception as e:
#                 print(e)
#
#
#     def stop_bot(self):
#         """Остановка бота"""
#         if self.process:
#             print("Остановка бота...")
#             self.running = False
#             self.response_queue.put(None)  # сигнал остановки потока записи
#             time.sleep(0.5)
#
#             try:
#                 self.process.terminate()
#                 self.process.wait(timeout=5)
#             except subprocess.TimeoutExpired:
#                 self.process.kill()
#                 self.process.wait()
#
#             print("Бот остановлен")
#
#     def __del__(self):
#         """Деструктор"""
#         if self.running:
#             self.stop_bot()
