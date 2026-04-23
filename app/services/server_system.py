import json
import socket
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

import psutil

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
        self.current_core_id = ""

        self.server_host = "127.0.0.1"
        self.server_port = 25565

        self.startup_log_tail = deque(maxlen=10)
        self.pending_work_data_requests = []
        self.server_perf_initialized = False
        self.process_perf_initialized = False

    def _try_toggle_rcon(self, value=True):
        try:
            self.toggle_rcon_in_active_core(value)
        except (ValueError, FileNotFoundError):
            return

    @staticmethod
    def _active_core_selected() -> bool:
        with config_path("program_settings.json").open("r", encoding="utf-8") as file:
            settings = json.load(file)
        return bool(settings.get("active_core"))

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
                elif msg["command"] == "set_server_rcon":
                    self._try_toggle_rcon(msg.get("data"))
                elif msg["command"] == "server_command":
                    self.send_commands(msg["data"])
                elif msg["command"] == "server_rcon_command":
                    response_text = self.handle_server_rcon_command(msg.get("data", ""))
                    self._send(
                        {
                            "to_process": msg.get("from_process"),
                            "from_process": "server",
                            "command": "server_rcon_command",
                            "data": response_text,
                            "request_id": msg.get("request_id"),
                        }
                    )
                elif msg["command"] == "get_server_status":
                    self._try_toggle_rcon(True)
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
                    if not self._active_core_selected():
                        self._send(
                            {
                                "to_process": msg.get("from_process"),
                                "from_process": "server",
                                "command": "set_server_work_data",
                                "data": {},
                                "request_id": msg.get("request_id"),
                            }
                        )
                        continue

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

    @staticmethod
    def toggle_rcon_in_active_core(enable_rcon=None):
        with config_path("program_settings.json").open("r", encoding="utf-8") as file:
            settings = json.load(file)
        with config_path("cores.json").open("r", encoding="utf-8") as file:
            core_list = json.load(file)

        active_core = str(settings.get("active_core", ""))
        if not active_core:
            raise ValueError("active_core_not_selected")
        if active_core not in core_list:
            raise ValueError("active_core_not_found_in_cores")

        server_dir = core_list[active_core].get("core_folder", "")
        if not server_dir:
            raise ValueError("active_core_folder_not_set")

        properties_path = Path(server_dir) / "server.properties"
        if not properties_path.is_file():
            raise FileNotFoundError(f"server_properties_not_found: {properties_path}")

        text = properties_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        values = {}
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()

        current_enable = values.get("enable-rcon", "false").lower() == "true"
        target_enable = (not current_enable) if enable_rcon is None else bool(enable_rcon)
        target_values = {
            "enable-rcon": "true" if target_enable else "false",
            "rcon.port": "25575",
            "rcon.password": "VERY_STRONG_PASSWORD_HERE",
            "broadcast-rcon-to-ops": "false",
        }

        def upsert(items, key, value):
            prefix = f"{key}="
            for i, row in enumerate(items):
                if row.strip().startswith(prefix):
                    items[i] = f"{key}={value}"
                    return
            items.append(f"{key}={value}")

        for key, value in target_values.items():
            upsert(lines, key, value)

        final_text = "\n".join(lines)
        if text.endswith("\n"):
            final_text += "\n"

        properties_path.write_text(final_text, encoding="utf-8")

        return {
            "server_properties_path": str(properties_path),
            "enable_rcon": target_values["enable-rcon"],
            "rcon_port": target_values["rcon.port"],
            "rcon_password": target_values["rcon.password"],
            "broadcast_rcon_to_ops": target_values["broadcast-rcon-to-ops"],
        }

    def _send(self, payload):
        with self.conn_send_lock:
            self.conn.send(payload)

    @staticmethod
    def _write_varint(value: int) -> bytes:
        out = bytearray()
        while True:
            part = value & 0x7F
            value >>= 7
            if value:
                part |= 0x80
            out.append(part)
            if not value:
                break
        return bytes(out)

    @staticmethod
    def _read_exact(sock: socket.socket, count: int) -> bytes:
        data = bytearray()
        while len(data) < count:
            chunk = sock.recv(count - len(data))
            if not chunk:
                raise ConnectionError("socket_closed")
            data.extend(chunk)
        return bytes(data)

    def _read_varint_socket(self, sock: socket.socket) -> int:
        value = 0
        shift = 0
        for _ in range(5):
            byte = self._read_exact(sock, 1)[0]
            value |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                return value
            shift += 7
        raise ValueError("varint_too_big")

    @staticmethod
    def _read_varint_buffer(buf: bytes, start: int = 0):
        value = 0
        shift = 0
        idx = start
        for _ in range(5):
            byte = buf[idx]
            value |= (byte & 0x7F) << shift
            idx += 1
            if not (byte & 0x80):
                return value, idx
            shift += 7
        raise ValueError("varint_too_big")

    def _query_minecraft_version(self, host: str, port: int, timeout: float = 3.0):
        try:
            host_bytes = host.encode("utf-8")
            with socket.create_connection((host, port), timeout=timeout) as sock:
                sock.settimeout(timeout)

                # Handshake (next state = status)
                handshake_payload = (
                    self._write_varint(0)
                    + self._write_varint(754)
                    + self._write_varint(len(host_bytes))
                    + host_bytes
                    + int(port).to_bytes(2, "big")
                    + self._write_varint(1)
                )
                sock.sendall(self._write_varint(len(handshake_payload)) + handshake_payload)

                # Status request packet
                sock.sendall(self._write_varint(1) + self._write_varint(0))

                packet_len = self._read_varint_socket(sock)
                packet_data = self._read_exact(sock, packet_len)
                packet_id, idx = self._read_varint_buffer(packet_data, 0)
                if packet_id != 0:
                    return None
                json_len, idx = self._read_varint_buffer(packet_data, idx)
                raw_json = packet_data[idx: idx + json_len].decode("utf-8", errors="replace")
                payload = json.loads(raw_json)
                return payload.get("version", {}).get("name")
        except Exception:
            return None

    @staticmethod
    def _read_rcon_packet(sock: socket.socket):
        packet_len_raw = ServerSystem._read_exact(sock, 4)
        packet_len = int.from_bytes(packet_len_raw, "little", signed=True)
        if packet_len < 10:
            raise ValueError("rcon_invalid_packet_length")

        payload = ServerSystem._read_exact(sock, packet_len)
        request_id = int.from_bytes(payload[0:4], "little", signed=True)
        packet_type = int.from_bytes(payload[4:8], "little", signed=True)
        body_bytes = payload[8:-2]
        body = body_bytes.decode("utf-8", errors="replace")
        return request_id, packet_type, body

    @staticmethod
    def _write_rcon_packet(sock: socket.socket, request_id: int, packet_type: int, body: str):
        body_bytes = (body or "").encode("utf-8")
        payload = (
            int(request_id).to_bytes(4, "little", signed=True)
            + int(packet_type).to_bytes(4, "little", signed=True)
            + body_bytes
            + b"\x00\x00"
        )
        sock.sendall(len(payload).to_bytes(4, "little", signed=True) + payload)

    @staticmethod
    def _get_rcon_params_from_active_core():
        with config_path("program_settings.json").open("r", encoding="utf-8") as file:
            settings = json.load(file)
        with config_path("cores.json").open("r", encoding="utf-8") as file:
            core_list = json.load(file)

        active_core = str(settings.get("active_core", ""))
        if not active_core:
            raise ValueError("active_core_not_selected")
        if active_core not in core_list:
            raise ValueError("active_core_not_found_in_cores")

        server_dir = core_list[active_core].get("core_folder", "")
        if not server_dir:
            raise ValueError("active_core_folder_not_set")

        properties_path = Path(server_dir) / "server.properties"
        if not properties_path.is_file():
            raise FileNotFoundError(f"server_properties_not_found: {properties_path}")

        props = {}
        for row in properties_path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = row.strip()
            if stripped and not stripped.startswith("#") and "=" in row:
                key, value = row.split("=", 1)
                props[key.strip()] = value.strip()

        if props.get("enable-rcon", "false").lower() != "true":
            raise ValueError("rcon_disabled")

        host = props.get("server-ip") or "127.0.0.1"
        port = int(props.get("rcon.port", "25575"))
        password = props.get("rcon.password", "")
        if not password:
            raise ValueError("rcon_password_not_set")
        return host, port, password

    def execute_rcon_command(self, command: str, timeout: float = 5.0) -> str:
        host, port, password = self._get_rcon_params_from_active_core()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)

            self._write_rcon_packet(sock, request_id=1, packet_type=3, body=password)
            auth_id, _, _ = self._read_rcon_packet(sock)
            if auth_id == -1:
                raise PermissionError("rcon_auth_failed")

            self._write_rcon_packet(sock, request_id=2, packet_type=2, body=command)
            response_id, _, response_body = self._read_rcon_packet(sock)
            if response_id == -1:
                raise PermissionError("rcon_command_rejected")

            response_parts = [response_body] if response_body else []
            sock.settimeout(0.05)
            while True:
                try:
                    next_response_id, _, next_response_body = self._read_rcon_packet(sock)
                except socket.timeout:
                    break

                if next_response_id == -1:
                    raise PermissionError("rcon_command_rejected")
                if next_response_id != response_id:
                    break
                if next_response_body:
                    response_parts.append(next_response_body)

            return "\n".join(response_parts).replace("\r\n", "\n").replace("\r", "\n")

    def handle_server_rcon_command(self, command: str) -> str:
        try:
            if not isinstance(command, str):
                return "rcon_invalid_command_type"
            cmd = command.strip()
            if not cmd:
                return "rcon_empty_command"
            return self.execute_rcon_command(cmd)
        except Exception as exc:
            return f"rcon_command_failed: {exc}"

    @staticmethod
    def _save_minecraft_version(core_id: str, version: str):
        if not core_id:
            return
        with config_path("cores.json").open("r", encoding="utf-8") as file:
            cores_all = json.load(file)
        if core_id not in cores_all:
            return
        cores_all[core_id]["minecraft_version"] = version
        with config_path("cores.json").open("w", encoding="utf-8") as file:
            json.dump(cores_all, file, ensure_ascii=False, indent=4)

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
        work_time = round(time.time() - server_work_started_at,
                          2) if status and server_work_started_at is not None else None
        system_metrics = self._read_system_metrics()
        xmx_mb = self._read_active_core_xmx_mb()
        server_process_metrics = self._read_server_process_metrics(system_metrics.get("ram_total_bytes"), xmx_mb)

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
            "server_xmx_mb": xmx_mb if xmx_mb is not None else "",
            "server_xmx_gb": round(xmx_mb / 1024, 2) if xmx_mb is not None else "",
            "system_metrics": system_metrics,
            "server_process_metrics": server_process_metrics,
        }

    def _read_system_metrics(self):
        if not self.server_perf_initialized:
            psutil.cpu_percent(interval=None)
            self.server_perf_initialized = True

        vm = psutil.virtual_memory()
        return {
            "cpu_percent": round(psutil.cpu_percent(interval=None), 2),
            "ram_percent": round(vm.percent, 2),
            "ram_used_gb": round(vm.used / (1024 ** 3), 2),
            "ram_total_gb": round(vm.total / (1024 ** 3), 2),
            "ram_total_bytes": vm.total,
        }

    @staticmethod
    def _read_active_core_xmx_mb():
        try:
            with config_path("program_settings.json").open("r", encoding="utf-8") as file:
                settings = json.load(file)
            active_core = str(settings.get("active_core", ""))
            if not active_core:
                return None

            with config_path("cores.json").open("r", encoding="utf-8") as file:
                cores = json.load(file)

            xmx = cores.get(active_core, {}).get("xmx")
            if xmx is None:
                return None

            xmx_mb = int(xmx)
            return xmx_mb if xmx_mb > 0 else None
        except Exception:
            return None

    def _read_server_process_metrics(self, system_ram_total_bytes=None, xmx_mb=None):
        if not self.is_running() or self.process is None:
            return {
                "is_running": False,
                "pid": "",
                "cpu_percent": "",
                "ram_rss_mb": "",
                "ram_rss_gb": "",
                "ram_percent_of_system": "",
                "ram_percent_of_xmx": "",
                "xmx_mb": xmx_mb if xmx_mb is not None else "",
                "xmx_gb": round(xmx_mb / 1024, 2) if xmx_mb is not None else "",
            }

        try:
            proc = psutil.Process(self.process.pid)
            if not self.process_perf_initialized:
                proc.cpu_percent(interval=None)
                self.process_perf_initialized = True

            cpu_raw = proc.cpu_percent(interval=0.2)
            cpu_percent = round(cpu_raw, 2)

            rss_bytes = proc.memory_info().rss
            rss_mb = round(rss_bytes / (1024 ** 2), 2)
            rss_gb = round(rss_bytes / (1024 ** 3), 2)

            ram_percent_of_system = ""
            if system_ram_total_bytes:
                ram_percent_of_system = round((rss_bytes / system_ram_total_bytes) * 100, 2)

            ram_percent_of_xmx = ""
            if xmx_mb:
                ram_percent_of_xmx = round((rss_mb / xmx_mb) * 100, 2)

            return {
                "is_running": True,
                "pid": proc.pid,
                "cpu_percent": cpu_percent,
                "ram_rss_mb": rss_mb,
                "ram_rss_gb": rss_gb,
                "ram_percent_of_system": ram_percent_of_system,
                "ram_percent_of_xmx": ram_percent_of_xmx,
                "xmx_mb": xmx_mb if xmx_mb is not None else "",
                "xmx_gb": round(xmx_mb / 1024, 2) if xmx_mb is not None else "",
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            self.process_perf_initialized = False
            return {
                "is_running": False,
                "pid": "",
                "cpu_percent": "",
                "ram_rss_mb": "",
                "ram_rss_gb": "",
                "ram_percent_of_system": "",
                "ram_percent_of_xmx": "",
                "xmx_mb": xmx_mb if xmx_mb is not None else "",
                "xmx_gb": round(xmx_mb / 1024, 2) if xmx_mb is not None else "",
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
                self.current_core_id = ""

            self._send({"to_process": "gui", "from_process": "server", "command": "error_out",
                        "data": "core_file_not_found_or_selected"})
            self._flush_pending_work_data_requests()
            return

        core_info = core_list[settings["active_core"]]
        self.current_core_id = str(settings["active_core"])
        core = Path(core_info["core_folder"]) / (f"{settings['active_core']}_{core_info['name']}")
        full_core_path = core.absolute()
        server_directory = full_core_path.parent

        def _memory_mb(key: str, default: int):
            value = core_info.get(key, default)
            try:
                value = int(value)
            except Exception:
                value = default
            return max(value, 64)

        xms_mb = _memory_mb("xms", 256)
        xmx_mb = _memory_mb("xmx", 1024)
        if xmx_mb < xms_mb:
            xmx_mb = xms_mb

        try:
            self.process = subprocess.Popen(
                [
                    "java",
                    "-Dfile.encoding=UTF-8",
                    f"-Xmx{xmx_mb}M",
                    f"-Xms{xms_mb}M",
                    "-jar",
                    str(full_core_path),
                    "nogui",
                ],
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
            self.process_perf_initialized = False
        except Exception as exc:
            with self.state_lock:
                self.is_starting = False
                self.last_start_duration = 0.0
                self.start_error = f"start_server_failed: {exc}"
                self.current_core_id = ""

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

        self.stdout_thread = threading.Thread(target=self.read_output, args=(self.process.stdout, "STDOUT"),
                                              daemon=True)
        self.stderr_thread = threading.Thread(target=self.read_output, args=(self.process.stderr, "STDERR"),
                                              daemon=True)
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
            self.current_core_id = ""
            self.process_perf_initialized = False
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

        if ok and self.is_running() and self.current_core_id:
            version = self._query_minecraft_version(self.server_host, self.server_port)
            if version:
                try:
                    self._save_minecraft_version(self.current_core_id, version)
                    self._send(
                        {
                            "to_process": "gui",
                            "from_process": "server",
                            "command": "set_server_version",
                            "data": {"core_id": self.current_core_id, "minecraft_version": version},
                        }
                    )
                except Exception:
                    pass

        self._flush_pending_work_data_requests()


def run(conn):
    ServerSystem(conn).run()
