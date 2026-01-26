from multiprocessing import Process, Pipe
import time
import threading
import sys
from PyQt5.QtWidgets import QApplication

class ProcessConnector:
    def __init__(self):
        self.bot_process = None
        self.server_process = None
        self.ui_process = None
        self.bot_parent_conn = None
        self.ui_parent_conn = None
        self.bot_prefix = "[ BOT ]"
        self.ui_prefix = "[ UI ]"
        self.server_prefix = "[ SERVER ]"
        self.main_prefix = "[ MAIN ]"
        self.main_parent_conn, self.main_child_conn = Pipe()

    def run(self):
        self.ui_start()

    def bot_start(self):
        if not self.bot_process:
            self.bot_parent_conn, bot_child_conn = Pipe()
            from bot import run_bot
            self.bot_process = Process(
                target=run_bot,
                args=(bot_child_conn,),
                daemon=True
            )
            self.bot_process.start()
            threading.Thread(
                target=self._read_from_bot,
                daemon=True
                ).start()
        else:
            print(self.bot_prefix ,"Бот уже запущен!")

    def ui_start(self):
        print(self.ui_process)
        if self.ui_process is None:
            self.ui_parent_conn, ui_child_conn = Pipe()
            from main_ui import run
            self.ui_process = Process(
                target=run,
                args=(ui_child_conn,),
                daemon=True
            )
            self.ui_process.start()
            threading.Thread(
                target=self._read_from_ui,
                daemon=True
            ).start()
        else:
            print("UI уже запущен!")

    def _read_from_ui(self):
        while True:
            try:
                msg = self.ui_parent_conn.recv()
                print(self.ui_prefix, msg)

            except EOFError:
                print(self.bot_prefix ,"Канал закрыт, завершаем чтение")
                break
            except Exception as e:
                print(self.bot_prefix ,f"Ошибка чтения из канала: {e}")
                break

    def _read_from_bot(self):
        """Блокирующее чтение - поток ждет сообщения"""
        while True:
            try:
                # recv() блокируется, пока не придет сообщение
                msg = self.bot_parent_conn.recv()
                print(self.bot_prefix ,"Получено сообщение от бота:", msg)
                if msg["to_process"] == "server":
                    if msg["command"] == "switch":
                        # self.server_process = threading.Thread(
                        #     target=,
                        #     daemon=True
                        # )
                        pass

            except EOFError:
                print(self.ui_prefix ,"Канал закрыт, завершаем чтение")
                break
            except Exception as e:
                print(self.ui_prefix ,f"Ошибка чтения из канала: {e}")
                break

    def main_piling(self):
        while True:
            try:
                msg = self.main_parent_conn.recv()
                if msg["command"] == "start_bot":
                    self.bot_start()
                elif msg["command"] == "stop_bot":
                    print("Остановка бота...")
            except EOFError:
                print(self.main_prefix ,"Канал закрыт, завершаем чтение")
                break
            except Exception as e:
                print(self.main_prefix ,f"Ошибка чтения из канала: {e}")
                break


    def bot_get_state(self):
        return True if self.bot_process else False


if __name__ == '__main__':
    connector = ProcessConnector()


    # def run():
    #     print(1111111)
    #     threading.Thread(target=connector.ui_start, daemon=True).start()
    #     print(2222222)
    # run()

    connector.run()


    while True:
        time.sleep(5)





























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
