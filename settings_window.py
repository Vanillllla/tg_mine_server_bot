import json

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
from PyQt5.QtGui import QIcon

from thems_my import Themes

class SettingsWindow(QDialog):

    settingsChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        :type to_path: str
        """
        self.settings_path = 'program_settings.json'

        super().__init__(parent)
        uic.loadUi('settings_ui.ui', self)
        self.setWindowTitle("Servers Telegram controller")
        self.setWindowIcon(QIcon('icon.ico'))

        with open(self.settings_path, 'r', encoding='utf-8') as f:
            self.settings = json.load(f)

        if self.settings["autostart"] == True :
            self.autostart_checkBox.setChecked(True)
        else:
            self.autostart_checkBox.setChecked(False)

        current_theme = parent.settings.get("theme", "light")
        theme_index = {
            "light": 2,
            "dark": 1,
            "green": 3
        }.get(current_theme, 0)
        self.comboBox.setCurrentIndex(theme_index)


        self.autostart_checkBox.stateChanged.connect(self.autostart_checkbox_changed)

        self.saveOut.clicked.connect(self.save)
        self.saveOut_2.clicked.connect(self.close)

    def autostart_checkbox_changed(self):
        if self.autostart_checkBox.isChecked() :
            self.settings["autostart"] = True
        else:
            self.settings["autostart"] = False

    def save(self):
        """Сохранить настройки в файл"""
        theme_map = {
            0: "system",  # "Как в системе"
            1: "dark",
            2: "light",
            3: "green"
        }
        selected_theme = theme_map.get(self.comboBox.currentIndex(), "light")

        # Если выбрано "Как в системе", определи системную тему
        if selected_theme == "system":
            # Простая проверка - если светлый фон, то светлая тема
            app = QApplication.instance()
            bg_color = app.palette().window().color()
            if bg_color.lightness() > 128:
                selected_theme = "light"
            else:
                selected_theme = "dark"

        self.settings["theme"] = selected_theme
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)
        self.settingsChanged.emit()
        self.close()