import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.json_store import read_json, write_json_atomic
from app.core.settings import AppSettings
from app.models.server import (
    CreateServerInstanceRequest,
    ServerInstance,
    UpdateServerInstanceRequest,
)


class ServerInstanceService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    @property
    def active_server_id(self) -> str:
        panel = read_json(self.settings.panel_config_path, default={})
        return str(panel.get("server", {}).get("active_server_id", "") or "")

    def list_servers(self) -> list[ServerInstance]:
        return [
            ServerInstance(id=server_id, **payload)
            for server_id, payload in self._read_servers().items()
        ]

    def get_server(self, server_id: str) -> ServerInstance:
        servers = self._read_servers()
        if server_id not in servers:
            raise KeyError(server_id)
        return ServerInstance(id=server_id, **servers[server_id])

    def get_active_server(self) -> ServerInstance | None:
        active_id = self.active_server_id
        if not active_id:
            return None
        try:
            return self.get_server(active_id)
        except KeyError:
            return None

    def create_server(self, payload: CreateServerInstanceRequest) -> ServerInstance:
        servers = self._read_servers()
        if payload.id in servers:
            raise ValueError("server_already_exists")

        server_dir = Path(payload.server_dir) if payload.server_dir else self.settings.servers_dir / payload.id
        server_dir = server_dir.expanduser().resolve()
        self._ensure_server_dir_allowed(server_dir)
        server_dir.mkdir(parents=True, exist_ok=True)
        self._write_eula_file(server_dir, payload.eula_accept)

        instance = ServerInstance(
            id=payload.id,
            display_name=payload.display_name,
            server_dir=str(server_dir),
            jar_file=payload.jar_file,
            minecraft_version=payload.minecraft_version,
            server_type=payload.server_type,
            java_path=payload.java_path,
            xms_mb=payload.xms_mb,
            xmx_mb=payload.xmx_mb,
            jvm_args=payload.jvm_args,
            server_args=payload.server_args,
            eula_accept=payload.eula_accept,
            auto_restart=payload.auto_restart,
            startup_timeout=payload.startup_timeout,
        )
        servers[payload.id] = self._instance_payload(instance)
        self._write_servers(servers)

        if not self.active_server_id:
            self.activate_server(payload.id)
        return self.get_server(payload.id)

    def activate_server(self, server_id: str) -> ServerInstance:
        server = self.get_server(server_id)
        panel = read_json(self.settings.panel_config_path, default={})
        panel.setdefault("server", {})["active_server_id"] = server_id
        write_json_atomic(self.settings.panel_config_path, panel)
        return server

    def update_server(
        self,
        server_id: str,
        payload: UpdateServerInstanceRequest,
    ) -> ServerInstance:
        current = self.get_server(server_id)
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        data = current.model_dump()
        data.update(changes)
        data["updated_at"] = datetime.now(timezone.utc)
        updated = ServerInstance(**data)

        server_dir = Path(updated.server_dir).expanduser().resolve()
        self._ensure_server_dir_allowed(server_dir)

        servers = self._read_servers()
        servers[server_id] = self._instance_payload(updated)
        self._write_servers(servers)
        return self.get_server(server_id)

    def set_active_server_jar(self, jar_file: str) -> ServerInstance:
        server = self.get_active_server()
        if server is None:
            raise KeyError("active_server_not_selected")

        candidate = Path(jar_file.replace("\\", "/"))
        if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
            raise ValueError("jar_file_has_unsafe_path")
        if candidate.suffix.lower() != ".jar":
            raise ValueError("jar_file_must_be_jar")

        server_dir = Path(server.server_dir).expanduser().resolve()
        target = (server_dir / candidate).resolve()
        try:
            target.relative_to(server_dir)
        except ValueError as exc:
            raise ValueError("jar_file_must_be_inside_server_dir") from exc
        if not target.is_file():
            raise FileNotFoundError("jar_file_not_found")

        return self.update_server(server.id, UpdateServerInstanceRequest(jar_file=candidate.as_posix()))

    def delete_server(self, server_id: str, delete_files: bool = True) -> None:
        server = self.get_server(server_id)
        servers = self._read_servers()
        del servers[server_id]
        self._write_servers(servers)

        if self.active_server_id == server_id:
            panel = read_json(self.settings.panel_config_path, default={})
            panel.setdefault("server", {})["active_server_id"] = ""
            write_json_atomic(self.settings.panel_config_path, panel)

        if delete_files:
            server_dir = Path(server.server_dir).expanduser().resolve()
            self._ensure_server_dir_allowed(server_dir)
            if server_dir.exists():
                shutil.rmtree(server_dir)

    def _read_servers(self) -> dict[str, dict[str, Any]]:
        return read_json(self.settings.servers_config_path, default={})

    def _write_servers(self, servers: dict[str, dict[str, Any]]) -> None:
        write_json_atomic(self.settings.servers_config_path, servers)

    @staticmethod
    def _instance_payload(instance: ServerInstance) -> dict[str, Any]:
        payload = instance.model_dump(mode="json")
        payload.pop("id", None)
        return payload

    def _ensure_server_dir_allowed(self, server_dir: Path) -> None:
        allowed_root = self.settings.servers_dir.resolve()
        try:
            server_dir.relative_to(allowed_root)
        except ValueError as exc:
            raise ValueError("server_dir_must_be_inside_servers_root") from exc

    @staticmethod
    def _write_eula_file(server_dir: Path, accepted: bool) -> None:
        if accepted:
            (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
