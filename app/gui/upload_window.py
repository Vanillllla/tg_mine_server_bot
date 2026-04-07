import os
import shutil

from PyQt5 import uic
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QFileDialog

from app.core.dirs_manager import DirsManager
from app.core.paths import BASE_DIR, ui_path


class UploadWindow(QDialog):
    def __init__(self, parent=None, to_path=None):
        super().__init__(parent)
        uic.loadUi(ui_path("upload_window.ui"), self)
        self.manager = DirsManager()
        self.setAcceptDrops(True)
        self.upload_folder = BASE_DIR / to_path if to_path else BASE_DIR
        self.upload_folder.mkdir(parents=True, exist_ok=True)

        self.selectFileButton.clicked.connect(self.select_file)
        self.closeButton.clicked.connect(self.close)
        self.progressBar.setVisible(False)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [item.toLocalFile() for item in event.mimeData().urls()]
        for file_path in files:
            if file_path.endswith(".jar"):
                self.upload_file(file_path)
            else:
                self.label.setText("Неподдерживаемый формат файла! Загрузите .jar файл.")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Только jar файлы (*.jar)")
        if file_path:
            self.upload_file(file_path)

    def upload_file(self, file_path):
        try:
            self.progressBar.setVisible(True)
            self.progressBar.setValue(50)
            filename = os.path.basename(file_path)
            destination = self.upload_folder / filename
            shutil.copy2(file_path, destination)
            self.label.setText(f"Файл '{filename}' загружен!")
            self.manager.new_core_upload(filename)
            self.progressBar.setValue(100)
            QTimer.singleShot(2000, lambda: self.progressBar.setVisible(False))
        except Exception as exc:
            self.label.setText(f"Ошибка: {exc}")
            self.progressBar.setVisible(False)
