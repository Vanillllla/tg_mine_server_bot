import json
import os
import shutil
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import uic



class UploadWindow(QDialog):
    def __init__(self, parent=None, to_path=None):
        """
        :type to_path: str
        """
        super().__init__(parent)

        # Загружаем интерфейс из .ui файла

        uic.loadUi('upload_window.ui', self)

        with open(self.settings_path, 'r', encoding='utf-8') as f:
            self.settings = json.load(f)
        # Настраиваем drag-and-drop
        self.setAcceptDrops(True)

        # Создаем папку для загрузок
        self.upload_folder = to_path
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)

        # Подключаем кнопки
        self.selectFileButton.clicked.connect(self.select_file)
        self.closeButton.clicked.connect(self.close)

        # Изначально скрываем прогресс-бар
        self.progressBar.setVisible(False)

    def dragEnterEvent(self, event):
        """Когда файл перетаскивается в окно"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Когда файл отпускают в окне"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]

        for file_path in files:
            if file_path.endswith(".jar"):
                self.upload_file(file_path)
            else:
                self.statusLabel.setText(f"Не поддерживаемый формат файла! Загрузите .jar файл.")

    def select_file(self):
        """Выбор файла через диалоговое окно"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            "",
            "Только jar файлы (*.jar)"
        )
        if file_path:
            self.upload_file(file_path)

    def upload_file(self, file_path):
        """Загрузка файла в папку программы"""
        try:
            # Показываем прогресс
            self.progressBar.setVisible(True)
            self.progressBar.setValue(50)

            # Получаем имя файла
            filename = os.path.basename(file_path)
            destination = os.path.join(self.upload_folder, filename)

            # Копируем файл
            shutil.copy2(file_path, destination)

            # Обновляем статус
            self.statusLabel.setText(f"Файл '{filename}' загружен!")
            self.progressBar.setValue(100)

            # Через 2 секунды скрываем прогресс
            QTimer.singleShot(2000, lambda: self.progressBar.setVisible(False))

        except Exception as e:
            self.statusLabel.setText(f"Ошибка: {str(e)}")
            self.progressBar.setVisible(False)