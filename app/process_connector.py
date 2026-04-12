import json
import sys
import threading
from multiprocessing import Pipe, Process
from time import sleep

from app.core.paths import config_path


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
        self.main_prefix = "[ CONNECTOR ]"
        self.error_prefix = "[ ERROR ]"

        with config_path("program_settings.json").open("r", encoding="utf-8") as file:
            self.settings = json.load(file)
        self.debag_mode = self.settings["debag_mode"]

        self.main_parent_conn, self.main_child_conn = Pipe()

    def run(self):
        self.ui_start()
        self.server_start()
        if self.settings["autostart_bot"]:
            self.bot_start()
        self.main_polling()

    def bot_start(self):
        if (self.bot_process is None) or (not self.bot_process.is_alive()):
            self.bot_parent_conn, bot_child_conn = Pipe()
            from app.services.telegram_bot import run_bot

            self.bot_process = Process(target=run_bot, args=(bot_child_conn,), name="bot_process", daemon=True)
            self.bot_process.start()
            self.th_botRead = threading.Thread(target=self._read_from_bot, daemon=True)
            self.th_botRead.start()
        else:
            if self.debag_mode : print(self.bot_prefix, "Бот уже запущен!")

    def ui_start(self):
        if (self.ui_process is None) or (not self.ui_process.is_alive()):
            self.ui_parent_conn, ui_child_conn = Pipe()
            from app.gui.main_window import run

            self.ui_process = Process(target=run, args=(ui_child_conn,), name="gui_process", daemon=True)
            self.ui_process.start()
            threading.Thread(target=self._read_from_ui, daemon=True).start()
        else:
            if self.debag_mode : print("UI уже запущен!")

    def server_start(self):
        if (self.server_process is None) or (not self.server_process.is_alive()):
            self.server_parent_conn, server_child_conn = Pipe()
            from app.services.server_system import run

            self.server_process = Process(target=run, args=(server_child_conn,), name="server_process", daemon=True)
            self.server_process.start()
            threading.Thread(target=self._read_from_server, daemon=True).start()
        else:
            if self.debag_mode : print("Server_manager уже запущен!")

    def _read_from_server(self):
        while True:
            try:
                msg = self.server_parent_conn.recv()
                if self.debag_mode : print(self.server_prefix, msg)
                if msg["to_process"] == "connector":
                    self.main_child_conn.send(msg)
                elif msg["to_process"] == "gui":
                    self.ui_parent_conn.send(msg)
                elif msg["to_process"] == "bot":
                    if self.bot_parent_conn:
                        self.bot_parent_conn.send(msg)
            except EOFError:
                if self.debag_mode : print(self.server_prefix, "Канал закрыт, завершаем чтение")
                break
            except Exception as exc:
                if self.debag_mode : print(self.error_prefix + self.server_prefix, f"Ошибка чтения из канала: {exc}")
                break

    def _read_from_ui(self):
        while True:
            try:
                msg = self.ui_parent_conn.recv()
                if self.debag_mode : print(self.ui_prefix, msg)
                if msg["to_process"] == "connector":
                    self.main_child_conn.send(msg)
                elif msg["to_process"] == "server":
                    self.server_parent_conn.send(msg)
            except EOFError:
                if self.debag_mode : print(self.ui_prefix, "Канал закрыт, завершаем чтение")
                self.main_child_conn.send({"command": "exit"})
                break
            except Exception as exc:
                if self.debag_mode : print(self.ui_prefix, f"Ошибка чтения из канала: {exc}")
                break

    def _read_from_bot(self):
        while True:
            try:
                msg = self.bot_parent_conn.recv()
                if self.debag_mode : print(self.bot_prefix, msg)
                if msg["to_process"] == "connector":
                    self.main_child_conn.send(msg)
                elif msg["to_process"] == "server":
                    self.server_parent_conn.send(msg)
            except EOFError:
                if self.debag_mode : print(self.bot_prefix, "Канал закрыт, завершаем чтение")
                break
            except Exception as exc:
                if self.debag_mode : print(self.error_prefix + self.bot_prefix, f"Ошибка чтения из канала: {exc}")
                break

    def main_polling(self):
        while True:
            try:
                msg = self.main_parent_conn.recv()
                if msg["command"] == "bot_switch":
                    if (self.bot_process is None) or (not self.bot_process.is_alive()):
                        self.bot_start()
                        msg2 = {"to_process": "gui", "from_process": "connector", "command": "set_bot_status", "data": True}
                        if self.debag_mode : print(self.main_prefix, msg2)
                        self.ui_parent_conn.send(msg2)
                    else:
                        self.bot_process.terminate()
                        self.th_botRead.join(timeout=1)
                        msg2 = {"to_process": "gui", "from_process": "connector", "command": "set_bot_status", "data": False}
                        if self.debag_mode : print(self.main_prefix, msg2)
                        self.ui_parent_conn.send(msg2)
                elif msg["command"] == "reload_bot":
                    self.bot_process.terminate()
                    self.bot_process.join(timeout=1)
                    if self.bot_process.is_alive():
                        self.bot_process.kill()
                        self.bot_process.join(timeout=1)
                    msg2 = {"to_process": "gui", "from_process": "connector", "command": "set_bot_status",
                            "data": False}
                    if self.debag_mode : print(self.main_prefix, msg2)
                    self.ui_parent_conn.send(msg2)
                    self.bot_start()
                    msg3 = {"to_process": "gui", "from_process": "connector", "command": "set_bot_status", "data": True}
                    if self.debag_mode : print(self.main_prefix, msg3)
                    self.ui_parent_conn.send(msg3)

                elif msg["command"] == "get_bot_status":
                    msg2 = {
                            "to_process": "gui",
                            "from_process": "connector",
                            "command": "set_bot_status",
                            "data": self.bot_process.is_alive() if self.bot_process else False,
                        }
                    if self.debag_mode : print(self.main_prefix, msg2)
                    self.ui_parent_conn.send(msg2)
                elif msg["command"] == "restart":
                    pass
                elif msg["command"] == "exit":
                    self.server_parent_conn.send(
                        {"to_process": "server", "from_process": "gui", "command": "set_server_status", "data": False})
                    sys.exit()
            except EOFError:
                if self.debag_mode : print(self.main_prefix, "Канал закрыт, завершаем чтение")
                break
            except Exception as exc:
                if self.debag_mode : print(self.error_prefix + self.main_prefix, f"Ошибка чтения из канала: {exc}")
                break


def main():
    ProcessConnector().run()


if __name__ == "__main__":
    main()
