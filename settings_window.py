import json

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
from PyQt5.QtGui import QIcon



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
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)
        self.settingsChanged.emit()
        self.close()