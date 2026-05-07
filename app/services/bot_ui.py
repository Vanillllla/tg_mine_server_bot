from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.services.bot_keyboard import BUTTON_TEXTS_BY_LOCALE, KEYBOARD_LAYOUTS
from app.services.bot_locale import MESSAGES_BY_LOCALE

DEFAULT_LOCALE = "ru"

LOCALES = {
    "ru": {
        "buttons": BUTTON_TEXTS_BY_LOCALE["ru"],
        "messages": MESSAGES_BY_LOCALE["ru"],
    },
    "en": {
        "buttons": BUTTON_TEXTS_BY_LOCALE["en"],
        "messages": MESSAGES_BY_LOCALE["en"],
    },
}

BUTTON_ACTIONS = {
    "start_server_user": "start_server",
    "start_server_admin": "start_server",
    "stop_server_admin": "stop_server",
    "online": "online",
    "user_settings": "user_settings",
    "admin_settings": "admin_settings",
    "reload_bot": "reload_bot",
    "console": "console",
    "workload": "workload",
    "server_properties": "server_properties",
    "profile": "profile",
    "back": "back",
    "test": "test",
    "users_list": "users_list",
    "add_user": "add_user",
    "remove_user": "remove_user",
    "permissions": "permissions",
    "disable_start_notifications": "disable_start_notifications",
    "enable_start_notifications": "enable_start_notifications",
}

BUTTON_IDS_BY_ACTION = {}
for button_id, action_id in BUTTON_ACTIONS.items():
    BUTTON_IDS_BY_ACTION.setdefault(action_id, set()).add(button_id)

TEXT_TO_BUTTON_ID = {}
for locale_data in LOCALES.values():
    for button_id, button_text in locale_data["buttons"].items():
        TEXT_TO_BUTTON_ID[button_text] = button_id


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return DEFAULT_LOCALE
    locale = locale.lower()
    if locale.startswith("en"):
        return "en"
    return "ru"


def get_message(locale: str, key: str, **kwargs) -> str:
    normalized_locale = normalize_locale(locale)
    text = LOCALES[normalized_locale]["messages"].get(key)
    if text is None:
        text = LOCALES[DEFAULT_LOCALE]["messages"].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def get_button_id_by_text(text: str | None) -> str | None:
    if text is None:
        return None
    return TEXT_TO_BUTTON_ID.get(text)


def is_action_text(action_id: str, text: str | None) -> bool:
    button_id = get_button_id_by_text(text)
    if button_id is None:
        return False
    return button_id in BUTTON_IDS_BY_ACTION.get(action_id, set())


def _get_keyboard_layout_key(status: int, server_status: bool, menu: str) -> str | None:
    if status == 0:
        if menu == "main_menu":
            return "user_main_online" if server_status else "user_main_offline"
        if menu == "settings":
            return "user_settings"

    if status == 1:
        if menu in {"main", "main_menu"}:
            return "admin_main_online" if server_status else "admin_main_offline"
        if menu == "settings":
            return "admin_settings"
        if menu == "console":
            return "admin_console"

    return None


def build_keyboard(
    status: int = 0,
    server_status: bool = False,
    menu: str = "main_menu",
    locale: str = DEFAULT_LOCALE,
) -> ReplyKeyboardMarkup | None:
    normalized_locale = normalize_locale(locale)
    locale_data = LOCALES[normalized_locale]
    layout_key = _get_keyboard_layout_key(status=status, server_status=server_status, menu=menu)
    if layout_key is None:
        return None

    layout = KEYBOARD_LAYOUTS.get(layout_key, [])
    button_texts = locale_data["buttons"]
    fallback_button_texts = LOCALES[DEFAULT_LOCALE]["buttons"]

    keyboard = []
    for row in layout:
        keyboard_row = []
        for button_id in row:
            button_text = button_texts.get(button_id, fallback_button_texts.get(button_id, button_id))
            keyboard_row.append(KeyboardButton(text=button_text))
        keyboard.append(keyboard_row)

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )
