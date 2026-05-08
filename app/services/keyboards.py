from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.services.localization import Locales


loc = Locales(default_language="ru")


class Keyboard():
    def __init__(self):
        self.status = 0
        self.state = False
        self.language = "ru"


    def get_keyboard(self, menu: str, user, server) -> ReplyKeyboardMarkup:
        self.status = user["status"]
        self.state = server["status"]
        self.language = user["language"]

    def admin_main_menu(self,) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=loc.get_text("button.start_server", ))],
            ], resize_keyboard=True
        )