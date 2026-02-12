import os
import json
import subprocess
import time
import threading
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

                if msg["command"] == "set_server_status":
                    if not self.is_running():
                        self.start_server()
                        status = self.is_running()
                    else:
                        self.is_running()
                        self.stop_server()
                        status = False

                    ans = {"to_process": "gui", "from_process": "server", "command": "set_server_status",
                           "data": status, "request_id": msg.get("request_id")}
                    self.conn.send(ans)

                elif msg["command"] == "server_command":
                    self.send_commands(msg["data"])

                elif msg["command"] == "get_server_status":
                    status = self.is_running()
                    ans = {"to_process": "gui", "from_process": "server", "command": "set_server_status",
                           "data": status, "request_id": msg.get("request_id")}
                    self.conn.send(ans)

            except EOFError as e:
                print(self.conn, e)

    def is_running(self):
        if self.process is None:
            return False
        result = self.process.poll()
        if result is None:
            return True
        else:
            self.process = None
            return False

    def start_server(self):
        with open("program_settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)
        with open("cores.json", "r", encoding="utf-8") as f:
            core_list = json.load(f)
        if settings["active_core"] == "":
            msg = {"to_process": "gui", "from_process": "server", "command": "error_out", "data": 1}
            self.conn.send(msg)
            return
        core = Path(core_list[settings["active_core"]]["core_folder"] + "/" + settings["active_core"] + "_" +
                    core_list[settings["active_core"]]["name"])
        full_core_path = core.absolute()
        server_directory = full_core_path.parent
        print(full_core_path)

        self.process = subprocess.Popen(
            ['java', '-Xmx1024M', '-Xms256M', '-jar', str(full_core_path), 'nogui'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(server_directory)
        )

        self.stdout_thread = threading.Thread(
            target=self.read_output,
            args=(self.process.stdout, "STDOUT")
        )
        self.stderr_thread = threading.Thread(
            target=self.read_output,
            args=(self.process.stderr, "STDERR")
        )

        self.stdout_thread.daemon = True
        self.stderr_thread.daemon = True

        self.stdout_thread.start()
        self.stderr_thread.start()

    def stop_server(self):
        if self.is_running():
            try:
                if self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.write("stop\n")
                    self.process.stdin.flush()

                for _ in range(30):
                    time.sleep(1)
                    if not self.is_running():
                        break
                else:
                    self.process.terminate()
                    time.sleep(5)

                    if self.is_running():
                        self.process.kill()

                self.process.wait(timeout=10)
            except:
                pass

            if self.process:
                if self.process.stdin and not self.process.stdin.closed:
                    try:
                        self.process.stdin.close()
                    except:
                        pass
                self.process = None

    def read_output(self, stream, name):
        try:
            for line in iter(stream.readline, ''):
                print(f"[{name}] {line}", end='')
        finally:
            stream.close()

    def send_commands(self, command):
        print(command)
        if self.is_running():
            if not command.endswith('\n'):
                command += '\n'
            self.process.stdin.write(command)
            self.process.stdin.flush()
        else:
            self.process = None


def run(conn):
    server = ServerSystem(conn)
    server.run()