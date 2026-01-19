# Способ 1: Динамическая загрузка
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel

from upload_window import UploadWindow


class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main_ui.ui', self)
        self.setWindowTitle("Servers controller")


        self.upload_core_action.triggered.connect(self.open_upload_window)


        self.open_setings_action.triggered.connect(self.open_settings_window)


        self.exit_action.triggered.connect(self.close)
        self.to_trey_action.triggered.connect(self.to_trey_program)
        self.restart_action.triggered.connect(self.restart_program)





        self.initUI()


    def initUI(self):
        self.show()

    def open_upload_window(self, to_path = None ):
        """Открываем окно загрузки файлов"""
        self.upload_window = UploadWindow(self, "downloads_cores")  # self как родитель
        self.upload_window.show()

    def open_settings_window(self):
        print("open_settings_window")

    def restart_program(self):
        print("restart_program")

    def to_trey_program(self):
        print("to_trey_program")

    def close_program(self):
        self.close()

    def closeEvent(self, event):
        # Здесь можно сохранить настройки, спросить подтверждение
        reply = QMessageBox.question(
            self, 'Подтверждение',
            'Вы уверены, что хотите выйти?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()  # Закрыть
        else:
            event.ignore()  # Не закрывать

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())