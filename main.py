# Способ 1: Динамическая загрузка
import os
import subprocess
import sys



from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox
from PyQt5.QtWidgets import QMainWindow, QLabel
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon

from upload_window import UploadWindow


class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main_ui.ui', self)
        self.setWindowTitle("Servers Telegram controller")
        self.setWindowIcon(QIcon('icon.ico'))


        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon_tray.ico"))  # или QIcon.fromTheme()
        traymenu = QMenu()
        traymenu.addAction("Открыть").triggered.connect(self.show)
        traymenu.addAction("Выход").triggered.connect(self.close_program)
        self.tray_icon.setContextMenu(traymenu)


        self.upload_core_action.triggered.connect(self.open_upload_cores_window)


        self.open_setings_action.triggered.connect(self.open_settings_window)


        self.exit_action.triggered.connect(self.close_program)
        self.to_trey_action.triggered.connect(self.close)
        self.restart_action.triggered.connect(self.restart_program)

        self.initUI()



    def initUI(self):
        self.show()

    def open_upload_cores_window(self ):
        """Открываем окно загрузки файлов"""
        self.upload_window = UploadWindow(self, "downloads_cores")  # self как родитель
        self.upload_window.show()

    def open_settings_window(self):
        print("open_settings_window")

    def restart_program(self):
        """Полный перезапуск приложения"""
        QMessageBox.warning(self, "Перезапуск", "Приложение будет перезапущено")
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
        # Здесь можно сохранить настройки, спросить подтверждение

        self.hide()  # Скрываем окно
        self.tray_icon.show()  # Показываем иконку в трее
        event.ignore()  # Не закрываем программу



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())