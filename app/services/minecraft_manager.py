import asyncio
import os
import time
from asyncio.subprocess import Process
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - optional until dependencies are installed
    psutil = None

from app.models.server import ServerInstance, ServerStatus
from app.services.log_buffer import LogBuffer
from app.services.server_instances import ServerInstanceService


class MinecraftServerManager:
    def __init__(
        self,
        instance_service: ServerInstanceService,
        log_buffer: LogBuffer,
    ) -> None:
        self.instance_service = instance_service
        self.log_buffer = log_buffer
        self.process: Process | None = None
        self.status = ServerStatus.OFF
        self.current_server_id: str | None = None
        self.started_at: float | None = None
        self.start_error = ""
        self.exit_code: int | None = None
        self._stdout_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._monitor_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    def is_running(self) -> bool:
        return self.process is not None and self.process.returncode is None

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

            args = self._build_launch_args(server)
            try:
                self.process = await asyncio.create_subprocess_exec(
                    *args,
                    cwd=server.server_dir,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
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

    async def stop(self) -> None:
        async with self._lock:
            if not self.process:
                self.status = ServerStatus.OFF
                return
            self.status = ServerStatus.STOPPING
            proc = self.process

        if proc.returncode is None and proc.stdin is not None:
            try:
                proc.stdin.write(b"stop\n")
                await proc.stdin.drain()
            except Exception:
                pass

        try:
            await asyncio.wait_for(proc.wait(), timeout=30)
        except asyncio.TimeoutError:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()

        await self._finalize_process()

    async def restart(self) -> None:
        await self.stop()
        await self.start()

    async def kill(self) -> None:
        async with self._lock:
            proc = self.process
            self.status = ServerStatus.STOPPING if proc else ServerStatus.OFF
        if proc and proc.returncode is None:
            proc.kill()
            await proc.wait()
        await self._finalize_process()

    async def send_stdin_command(self, command: str) -> None:
        if not self.is_running() or self.process is None or self.process.stdin is None:
            raise RuntimeError("server_not_running")
        line = command.strip()
        if not line:
            raise RuntimeError("empty_command")
        server_id = self.current_server_id or "active"
        await self.log_buffer.append("stdin", server_id, f"> {line}")
        self.process.stdin.write((line + "\n").encode("utf-8"))
        await self.process.stdin.drain()

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
        return {"system": system, "process": process}

    async def shutdown(self) -> None:
        if self.process and self.process.returncode is None:
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

    @staticmethod
    def _validate_launch(server: ServerInstance) -> None:
        server_dir = Path(server.server_dir)
        if not server_dir.is_dir():
            raise FileNotFoundError(f"server_dir_not_found: {server_dir}")
        if not server.jar_path.is_file():
            raise FileNotFoundError(f"jar_file_not_found: {server.jar_path}")
        if not server.eula_accept:
            raise ValueError("eula_must_be_accepted_before_start")

    async def _read_stream(self, stream_name: str, server_id: str) -> None:
        if self.process is None:
            return
        stream = self.process.stdout if stream_name == "stdout" else self.process.stderr
        if stream is None:
            return
        while True:
            raw = await stream.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            await self.log_buffer.append(stream_name, server_id, line)
            if self.status == ServerStatus.STARTING and "Done (" in line and "For help" in line:
                self.status = ServerStatus.RUNNING

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
                self.exit_code = self.process.returncode
            self.process = None
            self.started_at = None
            self.current_server_id = None
            self.status = ServerStatus.OFF

    def _sync_process_state(self) -> None:
        if self.process and self.process.returncode is not None:
            self.exit_code = self.process.returncode
            self.process = None
            self.started_at = None
            self.current_server_id = None
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

