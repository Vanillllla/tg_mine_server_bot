from multiprocessing import Process, Pipe
import time
import threading
import sys
import json


class ProcessConnector:
    def __init__(self):
        self.server_parent_conn = None
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
        self.error_prefix = "[\033[31m ERROR \033[0m]"
        with open("program_settings.json", "r") as f:
            settings = json.load(f)
        self.settings = settings
        self.main_parent_conn, self.main_child_conn = Pipe()

    def run(self):
        self.ui_start()
        self.server_start()
        print(111)
        if self.settings["autostart_bot"]:
            self.bot_start()
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
                elif msg["to_process"] == "gui":
                    self.ui_parent_conn.send(msg)
            except EOFError:
                print(self.server_prefix,"Канал закрыт, завершаем чтение" )
                break
            except Exception as e:
                print(self.error_prefix + self.server_prefix,f"Ошибка чтения из канала: {e}")
                break

    def _read_from_ui(self):
        while True:
            try:
                msg = self.ui_parent_conn.recv()
                print(self.ui_prefix, msg)
                if msg["to_process"] == "connector":
                    self.main_child_conn.send(msg)
                elif msg["to_process"] == "server":
                    self.server_parent_conn.send(msg)

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
                elif msg["to_process"] == "server":
                    self.server_parent_conn.send(msg)
            except EOFError:
                print(self.bot_prefix, "Канал закрыт, завершаем чтение")
                break
            except Exception as e:
                print(self.error_prefix + self.bot_prefix ,f"Ошибка чтения из канала: {e}")
                break

    def main_poling(self):
        while True:
            try:
                msg = self.main_parent_conn.recv()
                if msg["command"] == "bot_switch":
                    if (self.bot_process is None) or (not self.bot_process.is_alive()) :
                        self.bot_start()
                        self.ui_parent_conn.send({"to_process": "ui","from_process": "connector", "command": "set_bot_status", "data": True})
                    else:
                        self.bot_process.terminate()
                        self.th_botRead.join(timeout=1)
                        self.ui_parent_conn.send({"to_process": "ui", "from_process": "connector", "command": "set_bot_status", "data": False})
                elif msg["command"] == "get_bot_status":
                    msg = {"to_process": "gui", "from_process": "connector", "command": "set_bot_status", "data": (self.bot_process.is_alive() if self.bot_process else False)}
                    self.ui_parent_conn.send(msg)
                elif msg["command"] == "restart":
                    pass
                elif msg["command"] == "exit":
                    sys.exit()
            except EOFError:
                print(self.main_prefix ,"Канал закрыт, завершаем чтение")
                break
            except Exception as e:
                print(self.error_prefix + self.main_prefix ,f"Ошибка чтения из канала: {e}")
                break


if __name__ == '__main__':
    connector = ProcessConnector()
    connector.run()

