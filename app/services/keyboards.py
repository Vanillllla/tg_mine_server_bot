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
        elif menu == "settings_menu1":
            return self.settings_menu1()
        elif menu == "settings_menu2":
            return self.settings_menu2()
        elif menu == "console_mode":
            return self.console_mode()

    def main_menu(self) -> ReplyKeyboardMarkup:
        if self.status == 1:
            return ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=loc.get_text("button.start_server", self.language) if not self.state
                    else loc.get_text("button.stop_server", self.language))],
                    [KeyboardButton(text=loc.get_text("button.fast_command", self.language)),
                     KeyboardButton(text=loc.get_text("button.chek_online", self.language))],
                    [KeyboardButton(text=loc.get_text("button.workload", self.language)),
                     KeyboardButton(text=loc.get_text("button.settings_menu", self.language))],
                    [KeyboardButton(text=loc.get_text("button.reload_bot", self.language)), ]
                ], resize_keyboard=True
            )
        elif self.status == 0:
            return ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=loc.get_text("button.start_server", self.language))],
                    [KeyboardButton(text=loc.get_text("button.chek_online", self.language)),
                     KeyboardButton(text=loc.get_text("button.settings", self.language))],
                ]
            )

    def settings_menu1(self) -> ReplyKeyboardMarkup:
        if self.status == 1:
            return ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=loc.get_text("button.console_mode", self.language)),
                     KeyboardButton(text=loc.get_text("button.notification_settings", self.language))],
                    [KeyboardButton(text=loc.get_text("button.nick_set", self.language)),
                     KeyboardButton(text=loc.get_text("button.users_settings", self.language))],
                    [KeyboardButton(text=loc.get_text("button.exit", self.language)),
                     KeyboardButton(text=loc.get_text("button.next_settings_menu", self.language))],
                ]
            )

    def settings_menu2(self) -> ReplyKeyboardMarkup:
        if self.status == 1:
            return ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=loc.get_text("button.help", self.language)),
                     KeyboardButton(text=loc.get_text("button.reload_bot", self.language))],
                    [KeyboardButton(text=loc.get_text("button.help_settings", self.language)),
                     KeyboardButton(text=loc.get_text("button.fast_command_settings", self.language))],
                    [KeyboardButton(text=loc.get_text("button.back", self.language)),
                     KeyboardButton(text=loc.get_text("button.wtf", self.language))],
                ]
            )

    def settings_menu_users(self) -> ReplyKeyboardMarkup:
        if self.status == 1:
            return ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=loc.get_text("button.add_adm", self.language)),
                     KeyboardButton(text=loc.get_text("button.del_adm", self.language))],
                    [KeyboardButton(text=loc.get_text("button.block_user", self.language)),
                     KeyboardButton(text=loc.get_text("button.unblock_user", self.language))],
                    [KeyboardButton(text=loc.get_text("button.exit", self.language)),]
                ]
            )
    def console_mode(self) -> ReplyKeyboardMarkup:
        if self.status == 1:
            return ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=loc.get_text("button.exit", self.language)),]
                ]
            )