import json
import subprocess
import threading
import time
from pathlib import Path

from app.core.paths import config_path


class ServerSystem:
    def __init__(self, conn):
        self.conn = conn
        self.process = None
        self.stdout_thread = None
        self.stderr_thread = None
        self.conn_send_lock = threading.Lock()

    def _send(self, payload):
        with self.conn_send_lock:
            self.conn.send(payload)

    def run(self):
        self._read_from_connector()

    def _read_from_connector(self):
        while True:
            try:
                msg = self.conn.recv()

                if msg["command"] == "set_server_status" and msg["data"] == True:
                    if not self.is_running():
                        self.start_server()
                        status = self.is_running()
                    else:
                        self.stop_server()
                        status = False

                    self._send(
                        {
                            "to_process": "gui",
                            "from_process": "server",
                            "command": "set_server_status",
                            "data": status,
                            "request_id": msg.get("request_id"),
                        }
                    )
                elif msg["command"] == "set_server_status" and msg["data"] == False:
                    pass
                elif msg["command"] == "server_command":
                    self.send_commands(msg["data"])
                elif msg["command"] == "get_server_status":
                    self._send(
                        {
                            "to_process": "gui",
                            "from_process": "server",
                            "command": "set_server_status",
                            "data": self.is_running(),
                            "request_id": msg.get("request_id"),
                        }
                    )
            except EOFError as exc:
                print(self.conn, exc)

    def is_running(self):
        if self.process is None:
            return False
        if self.process.poll() is None:
            return True
        self.process = None
        return False

    def start_server(self):
        with config_path("program_settings.json").open("r", encoding="utf-8") as file:
            settings = json.load(file)
        with config_path("cores.json").open("r", encoding="utf-8") as file:
            core_list = json.load(file)

        if settings["active_core"] == "":
            self._send({"to_process": "gui", "from_process": "server", "command": "error_out", "data": 1})
            return

        core = Path(core_list[settings["active_core"]]["core_folder"]) / (
            f"{settings['active_core']}_{core_list[settings['active_core']]['name']}"
        )
        full_core_path = core.absolute()
        server_directory = full_core_path.parent

        self.process = subprocess.Popen(
            ["java", "-Dfile.encoding=UTF-8", "-Xmx1024M", "-Xms256M", "-jar", str(full_core_path), "nogui"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(server_directory),
        )

        self.stdout_thread = threading.Thread(target=self.read_output, args=(self.process.stdout, "STDOUT"), daemon=True)
        self.stderr_thread = threading.Thread(target=self.read_output, args=(self.process.stderr, "STDERR"), daemon=True)
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
            except Exception:
                pass

            if self.process:
                if self.process.stdin and not self.process.stdin.closed:
                    try:
                        self.process.stdin.close()
                    except Exception:
                        pass
                self.process = None

    def read_output(self, stream, name):
        try:
            for line in iter(stream.readline, ""):
                print(f"[{name}] {line}", end="")
                self._send(
                    {
                        "to_process": "gui",
                        "from_process": "server",
                        "command": "server_log",
                        "data": {"line": line.rstrip("\n"), "stream": name},
                    }
                )
        finally:
            stream.close()

    def send_commands(self, command):
        if self.is_running():
            try:
                if not command.endswith("\n"):
                    command += "\n"
                self.process.stdin.write(command)
                self.process.stdin.flush()
            except Exception as exc:
                self._send(
                    {
                        "to_process": "gui",
                        "from_process": "server",
                        "command": "error_out",
                        "data": f"send_command_failed: {exc}",
                    }
                )
        else:
            self.process = None


def run(conn):
    ServerSystem(conn).run()
