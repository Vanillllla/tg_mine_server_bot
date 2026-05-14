import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.properties import ServerPropertiesResponse
from app.models.server import ServerInstance


BOOL_KEYS = {
    "allow-nether",
    "broadcast-rcon-to-ops",
    "enable-command-block",
    "enable-rcon",
    "enforce-whitelist",
    "generate-structures",
    "online-mode",
    "pvp",
    "spawn-animals",
    "spawn-monsters",
    "spawn-npcs",
    "white-list",
}

INT_RANGES = {
    "server-port": (1, 65535),
    "max-players": (1, 100000),
    "view-distance": (2, 32),
    "simulation-distance": (2, 32),
}

ENUM_VALUES = {
    "difficulty": {"peaceful", "easy", "normal", "hard", "0", "1", "2", "3"},
    "gamemode": {"survival", "creative", "adventure", "spectator", "0", "1", "2", "3"},
}


class ServerPropertiesService:
    filename = "server.properties"

    def read(self, server: ServerInstance) -> ServerPropertiesResponse:
        path = self._path(server)
        if not path.exists():
            return ServerPropertiesResponse(exists=False, raw="", values={})
        raw = path.read_text(encoding="utf-8", errors="replace")
        return ServerPropertiesResponse(exists=True, raw=raw, values=self.parse(raw))

    def update_values(self, server: ServerInstance, values: dict[str, Any]) -> ServerPropertiesResponse:
        self._validate_values(values)
        path = self._path(server)
        raw = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        updated_raw = self._merge(raw, values)
        return self.write_raw(server, updated_raw)

    def write_raw(self, server: ServerInstance, raw: str) -> ServerPropertiesResponse:
        path = self._path(server)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            self._backup(path)
        path.write_text(raw.replace("\r\n", "\n"), encoding="utf-8")
        return self.read(server)

    @staticmethod
    def parse(raw: str) -> dict[str, str]:
        values: dict[str, str] = {}
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        return values

    @staticmethod
    def _merge(raw: str, values: dict[str, Any]) -> str:
        normalized = {key: ServerPropertiesService._stringify(value) for key, value in values.items()}
        seen: set[str] = set()
        lines: list[str] = []

        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                lines.append(line)
                continue
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in normalized:
                lines.append(f"{key}={normalized[key]}")
                seen.add(key)
            else:
                lines.append(line)

        missing = [key for key in normalized if key not in seen]
        if missing and lines and lines[-1].strip():
            lines.append("")
        for key in missing:
            lines.append(f"{key}={normalized[key]}")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _validate_values(values: dict[str, Any]) -> None:
        for key, value in values.items():
            text = ServerPropertiesService._stringify(value)
            if key in BOOL_KEYS and text not in {"true", "false"}:
                raise ValueError(f"{key}_must_be_bool")
            if key in INT_RANGES:
                minimum, maximum = INT_RANGES[key]
                try:
                    number = int(text)
                except ValueError as exc:
                    raise ValueError(f"{key}_must_be_int") from exc
                if number < minimum or number > maximum:
                    raise ValueError(f"{key}_must_be_between_{minimum}_and_{maximum}")
            if key in ENUM_VALUES and text not in ENUM_VALUES[key]:
                raise ValueError(f"{key}_has_unsupported_value")

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value).strip()

    @staticmethod
    def _path(server: ServerInstance) -> Path:
        return Path(server.server_dir) / ServerPropertiesService.filename

    @staticmethod
    def _backup(path: Path) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup = path.with_name(f"{path.name}.{stamp}.bak")
        shutil.copy2(path, backup)
