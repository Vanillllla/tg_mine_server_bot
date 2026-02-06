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
        threading.Thread(
            target=self._read_from_connector,
            daemon=True
        ).start()

    def _read_from_connector(self):
        while True:
            try:
                msg = self.conn.recv()
                print("print --> ", self.conn,msg)
                # ans = {"to_process": "bot", "from_process": "server", "command": "set_server_status", "data": False,
                #        "request_id": msg["request_id"]}
                if msg["command"] == "set_server_status":
                    if msg["data"] == True:
                        self.start_server()
                    elif msg["data"] == False:
                        # self.stop_server()
                        pass
                elif msg["command"] == "server_input":
                    print("didntwork")
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

        # Запускаем поток для отправки команд
        command_thread = threading.Thread(
            target=self.send_commands,
            args=(self.process,)
        )
        command_thread.daemon = True
        command_thread.start()



    def read_output(self, stream, name):
        """Чтение вывода из потока (stdout или stderr)"""
        for line in iter(stream.readline, ''):
            print(f"[{name}] {line}", end='')
        stream.close()

    def send_commands(self, process):
        """Отправка команд в процесс"""
        try:
            while process.poll() is None:  # пока процесс работает
                try:
                    # Читаем команду из консоли
                    command = input() + '\n'
                    process.stdin.write(command)
                    process.stdin.flush()
                except EOFError:
                    break
        except KeyboardInterrupt:
            print("\nОстановка сервера...")
            process.stdin.write('stop\n')
            process.stdin.flush()
            process.wait()

def run(conn):
    server = ServerSystem(conn)
    while True:
        time.sleep(1)