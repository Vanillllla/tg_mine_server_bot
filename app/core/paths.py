from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
RESOURCES_DIR = BASE_DIR / "resources"
UI_DIR = RESOURCES_DIR / "ui"
ASSETS_DIR = RESOURCES_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
DOWNLOADS_DIR = BASE_DIR / "downloads_cores"
SERVERS_DIR = BASE_DIR / "Servers"
USERS_DB_PATH = CONFIG_DIR / "users.db"


def config_path(filename: str) -> Path:
    return CONFIG_DIR / filename


def ui_path(filename: str) -> str:
    return str(UI_DIR / filename)


def icon_path(filename: str) -> str:
    return str(ICONS_DIR / filename)


def users_db_path() -> Path:
    return USERS_DB_PATH
