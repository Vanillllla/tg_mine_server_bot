import os
import json
import subprocess
import time
import threading
from os import name
from pathlib import Path


class ServerSystem:
    def __init__(self, conn):
        self.conn = conn
        self.process = None
        self.stdout_thread = None
        self.stderr_thread = None

    def run(self):
        self._read_from_connector()

    def _read_from_connector(self):
        while True:
            try:
                msg = self.conn.recv()
                # ans = {"to_process": "bot", "from_process": "server", "command": "set_server_status", "data": False,
                #        "request_id": msg["request_id"]}
                if msg["command"] == "set_server_status":
                    if self.process is None:
                        self.start_server()
                        ans = {"to_process": "gui", "from_process": "server", "command": "set_server_status",
                           "data": True if self.process is not None else False}
                    else:
                        self.stop_server()
                        ans = {"to_process": "gui", "from_process": "server", "command": "set_server_status",
                           "data": True if self.process is not None else False}
                    self.conn.send(ans)
                elif msg["command"] == "server_command":
                    print("print --> ", self.conn, msg)
                    self.send_commansds(msg["data"])
                elif msg["command"] == "get_server_status":
                    print(123123123123123)
                    ans = {"to_process": "gui", "from_process": "server", "command": "set_server_status", "data": True if self.process is not None else False}
                    self.conn.send(ans)
            except EOFError as e:
                print(self.conn, e)


    def start_server(self):
        with open("program_settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)
        with open("cores.json", "r", encoding="utf-8") as f:
            core_list = json.load(f)
        core = Path(core_list[settings["active_core"]]["core_folder"] + "/" + settings["active_core"] + "_" +
                    core_list[settings["active_core"]]["name"])
        full_core_path = core.absolute()
        server_directory = full_core_path.parent
        print(full_core_path)

        # Запускаем процесс с stdin для отправки команд
        self.process = subprocess.Popen(
            ['java', '-Xmx1024M', '-Xms256M', '-jar', str(full_core_path), 'nogui'],
            stdin=subprocess.PIPE,  # Добавили stdin
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Построчная буферизация
            cwd=str(server_directory)
        )

        # Запускаем потоки для чтения вывода
        self.stdout_thread = threading.Thread(
            target=self.read_output,
            args=(self.process.stdout, "STDOUT")
        )
        self.stderr_thread = threading.Thread(
            target=self.read_output,
            args=(self.process.stderr, "STDERR")
        )

        # Делаем потоки демонами, чтобы они завершились с основным потоком
        self.stdout_thread.daemon = True
        self.stderr_thread.daemon = True

        self.stdout_thread.start()
        self.stderr_thread.start()

    def stop_server(self):
        self.send_commansds("stop")
        time.sleep(5)
        if self.process.poll() is None:
            self.process.stdin.write('stop\n')
            time.sleep(5)
        if self.process.poll() is None:
            self.process.terminate()
            time.sleep(2)

    def read_output(self, stream, name):
        """Чтение вывода из потока (stdout или stderr)"""
        for line in iter(stream.readline, ''):
            print(f"[{name}] {line}", end='')
        stream.close()


    def send_commansds(self, command):
        """Отправка команд в процесс"""

        if self.process.poll() is None:
            self.process.stdin.write(command)
            self.process.stdin.flush()
        else:
            print("\nОстановка сервера...")
            self.process.stdin.write('stop\n')
            self.process.stdin.flush()
            self.process.wait()

def run(conn):
    server = ServerSystem(conn)
    server.run()