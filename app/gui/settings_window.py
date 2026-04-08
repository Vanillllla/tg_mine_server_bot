import json

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QDialog

from app.gui.i18n import normalize_language, t
from app.core.paths import config_path, icon_path, ui_path


class SettingsWindow(QDialog):
    settingsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_path = config_path("program_settings.json")
        uic.loadUi(ui_path("settings_ui.ui"), self)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon(icon_path("icon.ico")))

        with self.settings_path.open("r", encoding="utf-8") as file:
            self.settings = json.load(file)
        self.settings.setdefault("language", "ru")
        self.language = normalize_language(self.settings.get("language", "ru"))

        self.autostart_checkBox.setChecked(bool(self.settings["autostart"]))
        self.telegramBot_autostart_checkBox.setChecked(bool(self.settings["autostart_bot"]))
        if self.settings["telegram_bot_token"] != "":
            self.telegram_bot_token.setText(self.settings["telegram_bot_token"])

        if self.settings["serve_host_name"] != "":
            self.serve_host_name.setText(self.settings["serve_host_name"])

        current_theme = getattr(parent, "settings", {}).get("theme", self.settings.get("theme", "light"))
        theme_index = {"light": 2, "dark": 1, "green": 3}.get(current_theme, 0)
        self.comboBox.setCurrentIndex(theme_index)
        self.languageComboBox.setCurrentIndex({"ru": 0, "en": 1}.get(self.language, 0))
        self.apply_localization()

        self.autostart_checkBox.stateChanged.connect(self.autostart_checkbox_changed)
        self.telegramBot_autostart_checkBox.stateChanged.connect(self.telegram_bot_autostart_checkbox_changed)
        self.languageComboBox.currentIndexChanged.connect(self.language_changed)
        self.saveOut.clicked.connect(self.save)
        self.saveOut_2.clicked.connect(self.close)

    def autostart_checkbox_changed(self):
        self.settings["autostart"] = self.autostart_checkBox.isChecked()

    def telegram_bot_autostart_checkbox_changed(self):
        self.settings["autostart_bot"] = self.telegramBot_autostart_checkBox.isChecked()

    def language_changed(self):
        self.language = {0: "ru", 1: "en"}.get(self.languageComboBox.currentIndex(), "ru")
        self.apply_localization()

    def apply_localization(self):
        lang = self.language
        self.setWindowTitle(t(lang, "settings_title"))
        self.label.setText(t(lang, "settings_header"))
        self.generalGroupBox.setTitle(t(lang, "settings_group_general"))
        self.connectionGroupBox.setTitle(t(lang, "settings_group_connection"))
        self.autostart_checkBox.setText(t(lang, "settings_autostart"))
        self.telegramBot_autostart_checkBox.setText(t(lang, "settings_bot_autostart"))
        self.label_3.setText(t(lang, "settings_token"))
        self.label_4.setText(t(lang, "settings_host"))
        self.label_5.setText(t(lang, "settings_theme"))
        self.label_6.setText(t(lang, "settings_language"))
        self.saveOut.setText(t(lang, "settings_save"))
        self.saveOut_2.setText(t(lang, "settings_cancel"))

        self.telegram_bot_token.setPlaceholderText(t(lang, "token_placeholder"))
        self.serve_host_name.setPlaceholderText(t(lang, "host_placeholder"))

        self.comboBox.setItemText(0, t(lang, "theme_system"))
        self.comboBox.setItemText(1, t(lang, "theme_dark"))
        self.comboBox.setItemText(2, t(lang, "theme_light"))
        self.comboBox.setItemText(3, t(lang, "theme_green"))
        self.languageComboBox.setItemText(0, t(lang, "language_ru"))
        self.languageComboBox.setItemText(1, t(lang, "language_en"))

    def save(self):
        theme_map = {0: "system", 1: "dark", 2: "light", 3: "green"}
        selected_theme = theme_map.get(self.comboBox.currentIndex(), "light")
        selected_language = {0: "ru", 1: "en"}.get(self.languageComboBox.currentIndex(), "ru")
        self.settings["serve_host_name"] = self.serve_host_name.text()
        self.settings["telegram_bot_token"] = self.telegram_bot_token.text()

        if selected_theme == "system":
            app = QApplication.instance()
            bg_color = app.palette().window().color()
            selected_theme = "light" if bg_color.lightness() > 128 else "dark"

        self.settings["theme"] = selected_theme
        self.settings["language"] = selected_language
        with self.settings_path.open("w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=2, ensure_ascii=False)
        self.settingsChanged.emit()
        self.close()

