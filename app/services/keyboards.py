from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.services.localization import Locales


loc = Locales(default_language="ru")

# KeyboardButton(text=loc.get_text("button.", self.language))

class Keyboard:
    def __init__(self):
        self.status = 0
        self.state = False
        self.language = "ru"


    def get_keyboard(self, menu: str, profile_info, server_info) -> ReplyKeyboardMarkup:
        self.status = profile_info["status"]
        self.state = server_info["status"]
        self.language = profile_info["language"]
        if menu == "main_menu":
            return self.main_menu()

    def main_menu(self) -> ReplyKeyboardMarkup:
        if self.status == 1:
            return ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=loc.get_text("button.start_server", self.language) if not self.state
                    else loc.get_text("button.stop_server", self.language))],
                    [KeyboardButton(text=loc.get_text("button.fast_command", self.language)),
                     KeyboardButton(text=loc.get_text("button.chek_online", self.language))],
                    [KeyboardButton(text=loc.get_text("button.status", self.language)),
                     KeyboardButton(text=loc.get_text("button.settings", self.language))],
                    [KeyboardButton(text=loc.get_text("button.reload_bot", self.language)),]
                ], resize_keyboard=True
            )
        elif self.status == 2:
            return ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=loc.get_text("button.start_server", self.language))],
                    [KeyboardButton(text=loc.get_text("button.status", self.language)),
                     KeyboardButton(text=loc.get_text("button.settings", self.language))],

                ]
            )
        def settings_menu() -> ReplyKeyboardMarkup:
            if self.status:
                return ReplyKeyboardMarkup(

                )
            return ReplyKeyboardMarkup(

            )