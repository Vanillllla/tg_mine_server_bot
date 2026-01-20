import os
import subprocess
import sys
import json


from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox
from PyQt5.QtWidgets import QMainWindow, QLabel
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon

from upload_window import UploadWindow
from settings_window import SettingsWindow
from thems_my import Themes


class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.upload_window = None
        self.settings_window = None
        uic.loadUi('main_ui.ui', self)
        self.setWindowTitle("Servers Telegram controller")
        self.setWindowIcon(QIcon('icon.ico'))

        with open('program_settings.json', 'r', encoding='utf-8') as f:
            self.settings = json.load(f)

        self.apply_theme()

        # Монтируем трей
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon_tray.ico"))  # или QIcon.fromTheme()
        traymenu = QMenu()
        traymenu.addAction("Открыть").triggered.connect(self.show)
        traymenu.addAction("Выход").triggered.connect(self.close_program)
        self.tray_icon.setContextMenu(traymenu)


        ############################################################################### далее обработчики


        self.upload_core_action.triggered.connect(self.open_upload_cores_window)

        self.open_setings_action.triggered.connect(self.open_settings_window)


        self.printsettingsbutton.clicked.connect(self.printsettings)


        self.exit_action.triggered.connect(self.close_program)
        self.to_trey_action.triggered.connect(self.close)
        self.restart_action.triggered.connect(self.restart_program)

        self.action_GitHub.triggered.connect(self.open_github)

        self.initUI()



    def initUI(self):
        self.show()

    def printsettings(self):
        print(self.settings)

    def apply_theme(self):
        """Применяет текущую тему ко всему приложению"""
        theme_name = self.settings.get("theme", "light")
        stylesheet = Themes.get_theme(theme_name)
        app = QApplication.instance()
        app.setStyleSheet(stylesheet)

    def open_upload_cores_window(self ):
        """Открываем окно загрузки файлов"""
        self.upload_window = UploadWindow(self, "downloads_cores")  # self как родитель
        self.upload_window.exec_()
        self.apply_theme()

    def open_settings_window(self):
        self.settings_window = SettingsWindow(self)  # self как родитель
        # self.settings_window.settingsChanged.connect(self.load_settings)
        self.settings_window.settingsChanged.connect(self.load_settings)
        self.settings_window.exec_()


    def load_settings(self):
        with open('program_settings.json', 'r', encoding='utf-8') as f:
            self.settings = json.load(f)

    def open_github(self):
        """Открыть репозиторий GitHub"""
        QDesktopServices.openUrl(QUrl("https://github.com/Vanillllla/tg_mine_server_bot"))

    def restart_program(self):
        """Полный перезапуск приложения"""
        QApplication.quit()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def to_trey_program(self):
        print("to_trey_program")

    def close_program(self):
        # reply = QMessageBox.question(
        #     self, 'Подтверждение',
        #     'Вы уверены, что хотите выйти?',
        #     QMessageBox.Yes | QMessageBox.No,
        #     QMessageBox.No
        # )
        # if reply == QMessageBox.Yes:
        QApplication.quit()   # Закрыть

    def closeEvent(self, event):

        self.hide()  # Скрываем окно
        self.tray_icon.show()  # Показываем иконку в трее
        event.ignore()  # Не закрываем программу
        QApplication.quit()  # Закрыть






if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())


