import json
import os
import shutil
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import uic


class UploadWindow(QDialog):
    def __init__(self, parent=None, to_path=None):
        super().__init__(parent)
        uic.loadUi('upload_window.ui', self)

        self.setAcceptDrops(True)
        self.upload_folder = to_path
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)

        self.selectFileButton.clicked.connect(self.select_file)
        self.closeButton.clicked.connect(self.close)
        self.progressBar.setVisible(False)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            if file_path.endswith(".jar"):
                self.upload_file(file_path)
            else:
                self.label.setText(f"Не поддерживаемый формат файла! Загрузите .jar файл.")  # Изменено

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "", "Только jar файлы (*.jar)"
        )
        if file_path:
            self.upload_file(file_path)

    def upload_file(self, file_path):
        try:
            self.progressBar.setVisible(True)
            self.progressBar.setValue(50)
            filename = os.path.basename(file_path)
            destination = os.path.join(self.upload_folder, filename)
            shutil.copy2(file_path, destination)
            self.label.setText(f"Файл '{filename}' загружен!")  # Изменено
            self.progressBar.setValue(100)
            QTimer.singleShot(2000, lambda: self.progressBar.setVisible(False))
        except Exception as e:
            self.label.setText(f"Ошибка: {str(e)}")  # Изменено
            self.progressBar.setVisible(False)