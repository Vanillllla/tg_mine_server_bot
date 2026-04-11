import json
import socket
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

from app.core.paths import config_path


class ServerSystem:
    def __init__(self, conn):
        self.conn = conn
        self.process = None
        self.stdout_thread = None
        self.stderr_thread = None
        self.startup_thread = None
        self.conn_send_lock = threading.Lock()
        self.state_lock = threading.Lock()

        self.is_starting = False
        self.last_start_started_at = None
        self.last_start_duration = None
        self.start_error = ""
        self.server_work_started_at = None

        self.server_host = "127.0.0.1"
        self.server_port = 25565

        self.startup_log_tail = deque(maxlen=10)
        self.pending_work_data_requests = []

    def _send(self, payload):
        with self.conn_send_lock:
            self.conn.send(payload)

    def run(self):
        self._read_from_connector()

    def _format_ts(self, ts):
        if ts is None:
            return ""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

    def _build_work_data(self):
        with self.state_lock:
            is_starting = self.is_starting
            start_time = self.last_start_started_at
            launch_time = self.last_start_duration
            start_error = self.start_error
            server_work_started_at = self.server_work_started_at

        status = self.is_running()
        work_time = round(time.time() - server_work_started_at, 2) if status and server_work_started_at is not None else None

        return {
            "status": status,
            "is_starting": is_starting,
            "start_time": start_time if start_time is not None else "",
            "start_time_str": self._format_ts(start_time),
            "launch_time": launch_time if launch_time is not None else "",
            "launch_time_str": f"{launch_time:.2f} sec" if launch_time is not None else "",
            "work_time": work_time if work_time is not None else "",
            "work_time_str": f"{work_time:.2f} sec" if work_time is not None else "",
            "start_error": start_error,
        }

    def _send_work_data_response(self, msg):
        data = msg.get("data")
        payload_data = data.copy() if isinstance(data, dict) else {}
        payload_data.update(self._build_work_data())

        self._send(
            {
                "to_process": msg.get("from_process"),
                "from_process": "server",
                "command": "set_server_work_data",
                "data": payload_data,
                "request_id": msg.get("request_id"),
            }
        )

    def _flush_pending_work_data_requests(self):
        with self.state_lock:
            pending = self.pending_work_data_requests[:]
            self.pending_work_data_requests.clear()

        for msg in pending:
            self._send_work_data_response(msg)

    def _read_from_connector(self):
        while True:
            try:
                msg = self.conn.recv()

                if msg["command"] == "set_server_status" and msg["data"] == True:
                    if not self.is_running() and not self.is_starting:
                        self.start_server()
                        dabble_start_flag = False
                    else:
                        dabble_start_flag = True
                    status = self.is_running()
                    self._send(
                        {
                            "to_process": msg.get("from_process"),
                            "from_process": "server",
                            "command": "set_server_status",
                            "data": status,
                            "request_id": msg.get("request_id"),
                            "dabble_start_flag": dabble_start_flag,
                        }
                    )
                elif msg["command"] == "set_server_status" and msg["data"] == False:
                    if self.is_running() or self.is_starting:
                        self.stop_server()
                    status = self.is_running()
                    self._send(
                        {
                            "to_process": msg.get("from_process"),
                            "from_process": "server",
                            "command": "set_server_status",
                            "data": status,
                            "request_id": msg.get("request_id"),
                        }
                    )
                elif msg["command"] == "server_command":
                    self.send_commands(msg["data"])
                elif msg["command"] == "get_server_status":
                    self._send(
                        {
                            "to_process": msg.get("from_process"),
                            "from_process": "server",
                            "command": "set_server_status",
                            "data": self.is_running(),
                            "request_id": msg.get("request_id"),
                        }
                    )
                elif msg["command"] == "get_server_work_data":
                    should_send_now = False
                    with self.state_lock:
                        if self.is_starting:
                            self.pending_work_data_requests.append(msg)
                        else:
                            should_send_now = True
                    if should_send_now:
                        self._send_work_data_response(msg)

            except EOFError as exc:
                print(self.conn, exc)

    def is_running(self):
        if self.process is None:
            return False
        if self.process.poll() is None:
            return True
        self.process = None
        with self.state_lock:
            self.server_work_started_at = None
        return False

    def start_server(self):
        start_ts = time.time()

        with config_path("program_settings.json").open("r", encoding="utf-8") as file:
            settings = json.load(file)
        with config_path("cores.json").open("r", encoding="utf-8") as file:
            core_list = json.load(file)

        with self.state_lock:
            self.is_starting = True
            self.last_start_started_at = start_ts
            self.last_start_duration = None
            self.start_error = ""
            self.startup_log_tail.clear()

        if settings["active_core"] == "":
            with self.state_lock:
                self.is_starting = False
                self.last_start_duration = 0.0
                self.start_error = "core_file_not_found_or_selected"

            self._send({"to_process": "gui", "from_process": "server", "command": "error_out", "data": "core_file_not_found_or_selected"})
            self._flush_pending_work_data_requests()
            return

        core = Path(core_list[settings["active_core"]]["core_folder"]) / (
            f"{settings['active_core']}_{core_list[settings['active_core']]['name']}"
        )
        full_core_path = core.absolute()
        server_directory = full_core_path.parent

        try:
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
            with self.state_lock:
                self.server_work_started_at = time.time()
        except Exception as exc:
            with self.state_lock:
                self.is_starting = False
                self.last_start_duration = 0.0
                self.start_error = f"start_server_failed: {exc}"

            self._send(
                {
                    "to_process": "gui",
                    "from_process": "server",
                    "command": "error_out",
                    "data": f"start_server_failed: {exc}",
                }
            )
            self._flush_pending_work_data_requests()
            return

        self.stdout_thread = threading.Thread(target=self.read_output, args=(self.process.stdout, "STDOUT"), daemon=True)
        self.stderr_thread = threading.Thread(target=self.read_output, args=(self.process.stderr, "STDERR"), daemon=True)
        self.stdout_thread.start()
        self.stderr_thread.start()

        self.startup_thread = threading.Thread(target=self._monitor_startup, daemon=True)
        self.startup_thread.start()

    def stop_server(self):
        with self.state_lock:
            was_starting = self.is_starting

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

        with self.state_lock:
            self.server_work_started_at = None
            if was_starting:
                self.is_starting = False
                if self.last_start_started_at is not None and self.last_start_duration is None:
                    self.last_start_duration = round(time.time() - self.last_start_started_at, 2)
                if not self.start_error:
                    tail_text = "\n".join(self.startup_log_tail).strip()
                    self.start_error = tail_text if tail_text else "startup_stopped"

        if was_starting:
            self._flush_pending_work_data_requests()

    def read_output(self, stream, name):
        try:
            for line in iter(stream.readline, ""):
                clean_line = line.rstrip("\n")
                print(f"[{name}] {line}", end="")

                with self.state_lock:
                    self.startup_log_tail.append(f"[{name}] {clean_line}")

                self._send(
                    {
                        "to_process": "gui",
                        "from_process": "server",
                        "command": "server_log",
                        "data": {"line": clean_line, "stream": name},
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

    def _is_port_open(self, host=None, port=None, timeout=1.0):
        host = host or self.server_host
        port = port or self.server_port

        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def wait_for_server_ready_stable(self, max_wait=200, stable_count=3):
        start = time.time()
        success_count = 0

        while time.time() - start < max_wait:
            if not self.is_running():
                return False

            if self._is_port_open():
                success_count += 1
                if success_count >= stable_count:
                    return True
            else:
                success_count = 0

            time.sleep(1)

        return False

    def _monitor_startup(self):
        ok = self.wait_for_server_ready_stable()

        if not ok and self.is_running():
            self.stop_server()

        with self.state_lock:
            self.is_starting = False

            if self.last_start_started_at is not None and self.last_start_duration is None:
                self.last_start_duration = round(time.time() - self.last_start_started_at, 2)

            if ok and self.is_running():
                self.start_error = ""
            else:
                tail_text = "\n".join(self.startup_log_tail).strip()
                self.start_error = tail_text if tail_text else "server_start_timeout_or_crash"

        self._flush_pending_work_data_requests()


def run(conn):
    ServerSystem(conn).run()
