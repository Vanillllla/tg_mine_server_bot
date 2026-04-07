import json

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QDialog

from app.core.paths import config_path, icon_path, ui_path


class SettingsWindow(QDialog):
    settingsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_path = config_path("program_settings.json")
        uic.loadUi(ui_path("settings_ui.ui"), self)
        self.setWindowTitle("Servers Telegram controller")
        self.setWindowIcon(QIcon(icon_path("icon.ico")))

        with self.settings_path.open("r", encoding="utf-8") as file:
            self.settings = json.load(file)

        self.autostart_checkBox.setChecked(bool(self.settings["autostart"]))
        self.telegramBot_autostart_checkBox.setChecked(bool(self.settings["autostart_bot"]))

        if self.settings["telegram_bot_token"] == "":
            self.telegram_bot_token.setPlaceholderText("Your_bot_token")
        else:
            self.telegram_bot_token.setText(self.settings["telegram_bot_token"])

        if self.settings["serve_host_name"] == "":
            self.serve_host_name.setPlaceholderText("Your_host_name/ip")
        else:
            self.serve_host_name.setText(self.settings["serve_host_name"])

        current_theme = parent.settings.get("theme", "light")
        theme_index = {"light": 2, "dark": 1, "green": 3}.get(current_theme, 0)
        self.comboBox.setCurrentIndex(theme_index)

        self.autostart_checkBox.stateChanged.connect(self.autostart_checkbox_changed)
        self.telegramBot_autostart_checkBox.stateChanged.connect(self.telegram_bot_autostart_checkbox_changed)
        self.saveOut.clicked.connect(self.save)
        self.saveOut_2.clicked.connect(self.close)

    def autostart_checkbox_changed(self):
        self.settings["autostart"] = self.autostart_checkBox.isChecked()

    def telegram_bot_autostart_checkbox_changed(self):
        self.settings["autostart_bot"] = self.telegramBot_autostart_checkBox.isChecked()

    def save(self):
        theme_map = {0: "system", 1: "dark", 2: "light", 3: "green"}
        selected_theme = theme_map.get(self.comboBox.currentIndex(), "light")
        self.settings["serve_host_name"] = self.serve_host_name.text()
        self.settings["telegram_bot_token"] = self.telegram_bot_token.text()

        if selected_theme == "system":
            app = QApplication.instance()
            bg_color = app.palette().window().color()
            selected_theme = "light" if bg_color.lightness() > 128 else "dark"

        self.settings["theme"] = selected_theme
        with self.settings_path.open("w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=2, ensure_ascii=False)
        self.settingsChanged.emit()
        self.close()
