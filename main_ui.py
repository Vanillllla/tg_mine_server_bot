import os
import subprocess
import sys
import json


from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox
from PyQt5.QtWidgets import QMainWindow, QLabel
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtCore import QUrl, QTimer

from upload_window import UploadWindow
from settings_window import SettingsWindow
from thems_my import Themes
from process_connector import ProcessConnector

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.upload_window = None
        self.settings_window = None
        uic.loadUi('main_ui.ui', self)
        self.setWindowTitle("Servers Telegram controller")
        self.setWindowIcon(QIcon('icon.ico'))
        self.pc = ProcessConnector()

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
        ############################################################################### далее таймеры опросов

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)

        self.status_timer.start(2000)
        self.update_status()

        ############################################################################### далее обработчики


        self.upload_core_action.triggered.connect(self.open_upload_cores_window)

        self.open_setings_action.triggered.connect(self.open_settings_window)


        # self.printsettingsbutton.clicked.connect(self.printsettings)


        self.exit_action.triggered.connect(self.close_program)
        self.to_trey_action.triggered.connect(self.close)
        self.restart_action.triggered.connect(self.restart_program)

        self.action_GitHub.triggered.connect(self.open_github)

        self.bot_control_button.clicked.connect(self.start_bot)

        self.initUI()

    def update_status(self):
        """Опрос внешней функции и обновление статуса"""
        try:
            # Вызов вашей внешней функции
            is_active = self.pc.bot_get_state()  # Замените на вашу

            if is_active:
                self.botStatusLabel.setText("🟢 Сервер подключен")
                self.botStatusLabel.setStyleSheet("""
                    color: #2ecc71;
                    font-weight: bold;
                    padding: 5px;
                    background-color: rgba(46, 204, 113, 0.1);
                    border-radius: 3px;
                """)
            else:
                self.botStatusLabel.setText("🔴 Сервер недоступен")
                self.botStatusLabel.setStyleSheet("""
                    color: #e74c3c;
                    font-weight: bold;
                    padding: 5px;
                    background-color: rgba(231, 76, 60, 0.1);
                    border-radius: 3px;
                """)
        except Exception as e:
            self.botStatusLabel.setText("⚪ Ошибка проверки")
            print(f"Ошибка: {e}")


    def initUI(self):
        self.tray_icon.show()
        self.show()

    def printsettings(self):
        print(self.settings)

    def apply_theme(self):
        """Применяет текущую тему ко всему приложению"""
        theme_name = self.settings.get("theme", "light")
        stylesheet = Themes.get_theme(theme_name)
        app = QApplication.instance()
        app.setStyleSheet(stylesheet)

    def start_bot(self):
        self.pc.bot_start()
        # self.pc.ui_start()
        # pass

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
        reply = QMessageBox.question(
            self, 'Подтверждение',
            'Вы уверены, что хотите выйти?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QApplication.quit()   # Закрыть

    def closeEvent(self, event):

        self.hide()  # Скрываем окно
        self.tray_icon.show()  # Показываем иконку в трее
        event.ignore()  # Не закрываем программу
        QApplication.quit()  # Закрыть







# if __name__ = "__main__":
#     app = QApplication(sys.argv)
#     ex = MyApp()
#     sys.exit(app.exec_())
