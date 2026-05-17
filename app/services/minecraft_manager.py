import asyncio
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - optional until dependencies are installed
    psutil = None

from app.core.json_store import read_json
from app.models.server import ServerInstance, ServerStatus
from app.services.log_buffer import LogBuffer
from app.services.server_instances import ServerInstanceService


PLAYER_JOINED_RE = re.compile(r":\s*(?P<name>[A-Za-z0-9_]{1,16}) joined the game\b")
PLAYER_LEFT_RE = re.compile(r":\s*(?P<name>[A-Za-z0-9_]{1,16}) left the game\b")
TPS_RE = re.compile(r"\bTPS(?: from last [^:]+)?:\s*\*?(?P<tps>\d+(?:\.\d+)?)", re.IGNORECASE)
MINECRAFT_COLOR_RE = re.compile(r"§[0-9A-FK-ORa-fk-or]")


class MinecraftServerManager:
    def __init__(
        self,
        instance_service: ServerInstanceService,
        log_buffer: LogBuffer,
    ) -> None:
        self.instance_service = instance_service
        self.log_buffer = log_buffer
        self.process: subprocess.Popen | None = None
        self.status = ServerStatus.OFF
        self.current_server_id: str | None = None
        self.started_at: float | None = None
        self.start_error = ""
        self.exit_code: int | None = None
        self._stdout_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._monitor_task: asyncio.Task | None = None
        self._empty_shutdown_task: asyncio.Task | None = None
        self._tps_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._players_online: set[str] = set()
        self._last_empty_at: float | None = None
        self._last_tps: float | None = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    async def start(self) -> None:
        async with self._lock:
            if self.is_running() or self.status == ServerStatus.STARTING:
                raise RuntimeError("server_already_running")

            server = self.instance_service.get_active_server()
            if server is None:
                raise ValueError("active_server_not_selected")
            self._validate_launch(server)

            self.status = ServerStatus.STARTING
            self.current_server_id = server.id
            self.started_at = time.time()
            self.start_error = ""
            self.exit_code = None
            self._players_online = set()
            self._last_empty_at = time.time()
            self._last_tps = None

            args = self._build_launch_args(server)
            try:
                self.process = subprocess.Popen(
                    args,
                    cwd=server.server_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
            except Exception as exc:
                self.status = ServerStatus.ERROR
                self.start_error = f"start_failed: {exc}"
                self.process = None
                await self.log_buffer.append("stderr", server.id, self.start_error)
                raise

            self._stdout_task = asyncio.create_task(self._read_stream("stdout", server.id))
            self._stderr_task = asyncio.create_task(self._read_stream("stderr", server.id))
            self._monitor_task = asyncio.create_task(self._monitor_startup(server))
            self._empty_shutdown_task = asyncio.create_task(self._monitor_empty_shutdown(server.id))
            self._tps_task = asyncio.create_task(self._monitor_tps(server.id))

    async def stop(self) -> None:
        async with self._lock:
            if not self.process:
                self.status = ServerStatus.OFF
                return
            self.status = ServerStatus.STOPPING
            proc = self.process

        if proc.poll() is None and proc.stdin is not None:
            try:
                proc.stdin.write("stop\n")
                proc.stdin.flush()
            except Exception:
                pass

        try:
            await asyncio.to_thread(proc.wait, 30)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                await asyncio.to_thread(proc.wait, 5)
            except subprocess.TimeoutExpired:
                proc.kill()
                await asyncio.to_thread(proc.wait)

        await self._finalize_process()

    async def restart(self) -> None:
        await self.stop()
        await self.start()

    async def kill(self) -> None:
        async with self._lock:
            proc = self.process
            self.status = ServerStatus.STOPPING if proc else ServerStatus.OFF
        if proc and proc.poll() is None:
            proc.kill()
            await asyncio.to_thread(proc.wait)
        await self._finalize_process()

    async def send_stdin_command(self, command: str) -> None:
        await self._write_stdin_command(command, log=True)

    async def _write_stdin_command(self, command: str, log: bool) -> None:
        if not self.is_running() or self.process is None or self.process.stdin is None:
            raise RuntimeError("server_not_running")
        line = command.strip()
        if not line:
            raise RuntimeError("empty_command")
        server_id = self.current_server_id or "active"
        if log:
            await self.log_buffer.append("stdin", server_id, f"> {line}")
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def get_status(self) -> dict[str, Any]:
        self._sync_process_state()
        return {
            "status": self.status.value,
            "active_server_id": self.instance_service.active_server_id or None,
            "current_server_id": self.current_server_id,
            "pid": self.process.pid if self.process else None,
            "uptime_seconds": self._uptime_seconds(),
            "start_error": self.start_error,
            "exit_code": self.exit_code,
        }

    def get_work_data(self) -> dict[str, Any]:
        active = self.instance_service.get_active_server()
        return {
            **self.get_status(),
            "active_server": active.model_dump(mode="json") if active else None,
            "metrics": self.get_metrics(),
            "recent_logs": self.log_buffer.recent(limit=50),
        }

    def get_metrics(self) -> dict[str, Any]:
        system = self._system_metrics()
        process = self._process_metrics()
        minecraft = {"tps": self._last_tps if self.is_running() else None}
        return {"system": system, "process": process, "minecraft": minecraft}

    async def shutdown(self) -> None:
        if self.process and self.process.poll() is None:
            await self.stop()

    def _build_launch_args(self, server: ServerInstance) -> list[str]:
        return [
            server.java_path,
            f"-Xms{server.xms_mb}M",
            f"-Xmx{server.xmx_mb}M",
            *server.jvm_args,
            "-jar",
            str(Path(server.server_dir) / server.jar_file),
            *server.server_args,
        ]

    @classmethod
    def _validate_launch(cls, server: ServerInstance) -> None:
        server_dir = Path(server.server_dir)
        if not server_dir.is_dir():
            raise FileNotFoundError(f"server_dir_not_found: {server_dir}")
        if not server.jar_path.is_file():
            raise FileNotFoundError(f"jar_file_not_found: {server.jar_path}")
        if not cls._eula_file_is_accepted(server_dir / "eula.txt"):
            raise ValueError("eula_must_be_accepted_before_start")

    @staticmethod
    def _eula_file_is_accepted(path: Path) -> bool:
        if not path.is_file():
            return False
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            normalized = line.strip().lower()
            if not normalized or normalized.startswith("#"):
                continue
            if normalized == "eula=true":
                return True
            if normalized.startswith("eula="):
                return False
        return False

    async def _read_stream(self, stream_name: str, server_id: str) -> None:
        if self.process is None:
            return
        stream = self.process.stdout if stream_name == "stdout" else self.process.stderr
        if stream is None:
            return
        while True:
            line = await asyncio.to_thread(stream.readline)
            if not line:
                break
            line = line.rstrip("\r\n")
            await self.log_buffer.append(stream_name, server_id, line)
            if stream_name == "stdout":
                self._update_player_presence(line)
                self._update_tps(line)
            if self.status == ServerStatus.STARTING and "Done (" in line and "For help" in line:
                self.status = ServerStatus.RUNNING

    async def _monitor_tps(self, server_id: str) -> None:
        while self.is_running() and self.current_server_id == server_id:
            if self.status == ServerStatus.RUNNING:
                try:
                    await self._write_stdin_command("tps", log=False)
                except RuntimeError:
                    pass
                await asyncio.sleep(60)
                continue
            await asyncio.sleep(5)

    async def _monitor_empty_shutdown(self, server_id: str) -> None:
        while self.is_running() and self.current_server_id == server_id:
            settings = self._empty_shutdown_settings()
            if not settings["enabled"]:
                self._last_empty_at = time.time() if not self._players_online else None
                await asyncio.sleep(15)
                continue

            if self.status == ServerStatus.RUNNING and not self._players_online:
                if self._last_empty_at is None:
                    self._last_empty_at = time.time()
                if time.time() - self._last_empty_at >= settings["minutes"] * 60:
                    await self.log_buffer.append("stdout", server_id, "Auto shutdown: server is empty")
                    await self.stop()
                    return
            await asyncio.sleep(15)

    def _update_player_presence(self, line: str) -> None:
        event = self._player_event_from_log_line(line)
        if event is None:
            return
        action, name = event
        if action == "join":
            self._players_online.add(name)
            self._last_empty_at = None
            return
        self._players_online.discard(name)
        if not self._players_online:
            self._last_empty_at = time.time()

    def _update_tps(self, line: str) -> None:
        tps = self._tps_from_log_line(line)
        if tps is not None:
            self._last_tps = tps

    @staticmethod
    def _tps_from_log_line(line: str) -> float | None:
        normalized = MINECRAFT_COLOR_RE.sub("", line)
        match = TPS_RE.search(normalized)
        if not match:
            return None
        return round(min(float(match.group("tps")), 20.0), 2)

    @staticmethod
    def _player_event_from_log_line(line: str) -> tuple[str, str] | None:
        joined = PLAYER_JOINED_RE.search(line)
        if joined:
            return ("join", joined.group("name"))
        left = PLAYER_LEFT_RE.search(line)
        if left:
            return ("leave", left.group("name"))
        return None

    def _empty_shutdown_settings(self) -> dict[str, Any]:
        panel = read_json(self.instance_service.settings.panel_config_path, default={})
        server = panel.get("server", {})
        minutes = int(server.get("shutdown_if_empty_minutes", 5) or 5)
        return {
            "enabled": bool(server.get("shutdown_if_empty_enabled", False)),
            "minutes": max(1, minutes),
        }

    async def _monitor_startup(self, server: ServerInstance) -> None:
        deadline = time.time() + server.startup_timeout
        while time.time() < deadline:
            if not self.is_running():
                break
            if self.status == ServerStatus.RUNNING:
                return
            await asyncio.sleep(0.5)

        if self.is_running() and self.status == ServerStatus.STARTING:
            self.status = ServerStatus.RUNNING
            return

        if self.status == ServerStatus.STARTING:
            self.status = ServerStatus.ERROR
            self.start_error = "server_start_timeout_or_crash"

    async def _finalize_process(self) -> None:
        async with self._lock:
            if self.process:
                self.exit_code = self.process.poll()
            self.process = None
            self.started_at = None
            self.current_server_id = None
            self.status = ServerStatus.OFF
            self._last_tps = None

    def _sync_process_state(self) -> None:
        if self.process and self.process.poll() is not None:
            self.exit_code = self.process.poll()
            self.process = None
            self.started_at = None
            self.current_server_id = None
            self._last_tps = None
            if self.status not in {ServerStatus.ERROR, ServerStatus.STOPPING}:
                self.status = ServerStatus.OFF

    def _uptime_seconds(self) -> float | None:
        if not self.started_at or not self.is_running():
            return None
        return round(time.time() - self.started_at, 2)

    @staticmethod
    def _system_metrics() -> dict[str, Any]:
        if psutil is None:
            return {"available": False}
        vm = psutil.virtual_memory()
        return {
            "available": True,
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_total_mb": round(vm.total / (1024**2), 2),
            "ram_used_mb": round(vm.used / (1024**2), 2),
            "ram_percent": vm.percent,
        }

    def _process_metrics(self) -> dict[str, Any]:
        if psutil is None or not self.process or not self.is_running():
            return {"available": psutil is not None, "is_running": self.is_running()}
        try:
            proc = psutil.Process(self.process.pid)
            rss = proc.memory_info().rss
            return {
                "available": True,
                "is_running": True,
                "pid": proc.pid,
                "cpu_percent": proc.cpu_percent(interval=None),
                "ram_rss_mb": round(rss / (1024**2), 2),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return {"available": True, "is_running": False}
