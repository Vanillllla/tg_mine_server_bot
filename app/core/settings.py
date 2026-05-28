import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.json_store import write_json_atomic


DEFAULT_PANEL = {
    "panel": {"language": "ru", "theme": "dark", "debug_mode": False},
    "links": {
        "discord": {
            "url": "https://discord.gg/cUt6nYVEyn",
            "icon_path": "/assets/icons/discord.svg",
        },
    },
    "domains": {
        "minecraft": "mc.vanilla.xazux.ru",
        "site": "",
    },
    "server": {
        "active_server_id": "",
        "use_last_active_server": True,
        "shutdown_if_empty_enabled": False,
        "shutdown_if_empty_minutes": 5,
    },
    "telegram": {
        "autostart": False,
        "token_secret_id": "telegram_bot_token",
        "bot_token": "",
        "admin_ids": [],
    },
    "java": {"default_runtime_id": "", "runtimes": []},
}

DEFAULT_AUTH = {
    "invite": {"token": "", "created_at": None, "revoked_at": None},
    "sessions": {},
}


@dataclass(frozen=True)
class AppSettings:
    panel_home: Path
    log_buffer_lines: int = 5000

    @property
    def config_dir(self) -> Path:
        return self.panel_home / "config"

    @property
    def data_dir(self) -> Path:
        return self.panel_home / "data"

    @property
    def uploads_dir(self) -> Path:
        return self.panel_home / "uploads"

    @property
    def backups_dir(self) -> Path:
        return self.panel_home / "backups"

    @property
    def servers_dir(self) -> Path:
        return self.panel_home / "servers"

    @property
    def panel_config_path(self) -> Path:
        return self.config_dir / "panel.json"

    @property
    def servers_config_path(self) -> Path:
        return self.config_dir / "servers.json"

    @property
    def auth_config_path(self) -> Path:
        return self.config_dir / "auth.json"

    @property
    def mod_catalog_path(self) -> Path:
        return self.data_dir / "mods.json"

    @property
    def mod_cache_dir(self) -> Path:
        return self.data_dir / "mod-cache"

    def ensure_runtime_layout(self) -> None:
        for path in (
            self.config_dir,
            self.data_dir,
            self.mod_cache_dir,
            self.uploads_dir / "cores",
            self.uploads_dir / "worlds",
            self.uploads_dir / "temp",
            self.backups_dir / "properties",
            self.backups_dir / "worlds",
            self.backups_dir / "icons",
            self.servers_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

        if not self.panel_config_path.exists():
            write_json_atomic(self.panel_config_path, DEFAULT_PANEL)
        if not self.servers_config_path.exists():
            write_json_atomic(self.servers_config_path, {})
        if not self.auth_config_path.exists():
            write_json_atomic(self.auth_config_path, DEFAULT_AUTH)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    default_home = Path.cwd() / "runtime" / "mc-panel"
    panel_home = Path(os.getenv("MC_PANEL_HOME", str(default_home))).expanduser().resolve()
    lines = int(os.getenv("MC_PANEL_LOG_BUFFER_LINES", "5000"))
    return AppSettings(panel_home=panel_home, log_buffer_lines=max(lines, 300))
