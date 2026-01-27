from multiprocessing import Process, Pipe
import time
import threading
import sys
# import os
# os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

class ProcessConnector:
    def __init__(self):
        self.th_botRead = None
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
        self.main_poling()

    def bot_start(self):
        if (self.bot_process is None) or (not self.bot_process.is_alive()):
            self.bot_parent_conn, bot_child_conn = Pipe()
            from bot import run_bot
            self.bot_process = Process(
                target=run_bot,
                args=(bot_child_conn,),
                name="bot_process",
                daemon=True
            )
            self.bot_process.start()
            self.th_botRead = threading.Thread(
                target=self._read_from_bot,
                daemon=True
                )
            self.th_botRead.start()
        else:
            print(self.bot_prefix ,"Бот уже запущен!")

    def ui_start(self):
        if (self.ui_process is None) or (not self.ui_process.is_alive()):
            self.ui_parent_conn, ui_child_conn = Pipe()
            from main_ui import run
            self.ui_process = Process(
                target=run,
                args=(ui_child_conn,),
                name="ui_process",
                daemon=True
            )
            self.ui_process.start()
            threading.Thread(
                target=self._read_from_ui,
                daemon=True
            ).start()
        else:
            print("UI уже запущен!")

    def server_start(self):
        if (self.server_process is None) or (not self.server_process.is_alive()):
            self.server_parent_conn, server_child_conn = Pipe()
            from server_system import run
            self.server_process = Process(
                target=run,
                args=(server_child_conn,),
                name="server_process",
                daemon=True
            )
            self.server_process.start()
            threading.Thread(
                target=self._read_from_server,
                daemon=True
            ).start()

    def _read_from_server(self):
        while True:
            try:
                msg = self.server_parent_conn.recv()
                print(self.server_prefix,msg)
                if msg["to_process"] == "connector":
                    self.main_child_conn.send(msg)
            except EOFError:
                print(self.server_prefix,"Канал закрыт, завершаем чтение" )
                break
            except Exception as e:
                print(self.server_prefix,f"Ошибка чтения из канала: {e}")
                break

    def _read_from_ui(self):
        while True:
            try:
                msg = self.ui_parent_conn.recv()
                print(self.ui_prefix, msg)
                if msg["to_process"] == "connector":
                        self.main_child_conn.send(msg)

            except EOFError:
                print(self.ui_prefix ,"Канал закрыт, завершаем чтение")
                break
            except Exception as e:
                print(self.ui_prefix ,f"Ошибка чтения из канала: {e}")
                break

    def _read_from_bot(self):
        while True:
            try:
                msg = self.bot_parent_conn.recv()
                print(self.bot_prefix, msg)
                if msg["to_process"] == "connector":
                    self.main_child_conn.send(msg)

            except EOFError:
                print(self.bot_prefix, "Канал закрыт, завершаем чтение")
                break
            except Exception as e:
                print(self.bot_prefix ,f"Ошибка чтения из канала: {e}")
                break

    def main_poling(self):
        while True:
            try:
                msg = self.main_parent_conn.recv()
                if msg["command"] == "bot_switch":
                    if (self.bot_process is None) or (not self.bot_process.is_alive()) :
                        self.bot_start()
                        self.ui_parent_conn.send({"to_process": "ui", "command": "set_bot_status", "data": True})
                    else:
                        self.bot_process.terminate()
                        self.th_botRead.join(timeout=1)
                        self.ui_parent_conn.send({"to_process": "ui", "command": "set_bot_status", "data": False})
                elif msg["command"] == "server_switch":
                    if (self.server_process is None) or (not self.server_process.is_alive()) :
                        self.server_start()
                        self.ui_parent_conn.send({"to_process": "ui", "command": "set_server_status", "data": True})
                        self.server_parent_conn.send({"to_process": "server", "command": "start", "data": None})
                    else:

                        self.ui_parent_conn.send({"to_process": "ui", "command": "set_server_status", "data": False})

                if msg["command"] == "exit":
                    sys.exit()
            except EOFError:
                print(self.main_prefix ,"Канал закрыт, завершаем чтение")
                break
            except Exception as e:
                print(self.main_prefix ,f"Ошибка чтения из канала: {e}")
                break


    def bot_get_state(self):
        print(self.bot_process.is_alive())
        return False

if __name__ == '__main__':
    connector = ProcessConnector()
    connector.run()

