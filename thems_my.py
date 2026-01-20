from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt


class Themes:
    @staticmethod
    def get_theme(name):
        if name == "dark":
            return Themes.dark_theme()
        elif name == "green":
            return Themes.green_theme()
        else:  # "light" or default
            return Themes.light_theme()

    @staticmethod
    def light_theme():
        """Светлая тема (стандартная)"""
        return """
            QMainWindow, QDialog, QWidget {
                background-color: #f0f0f0;
                color: #000000;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #a0a0a0;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #a0a0a0;
                border-radius: 3px;
                padding: 3px;
            }
            QCheckBox {
                spacing: 5px;
            }
            QComboBox {
                border: 1px solid #a0a0a0;
                border-radius: 3px;
                padding: 3px;
                background-color: white;
            }
            QLabel {
                color: #000000;
            }
            QProgressBar {
                border: 1px solid #a0a0a0;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QMenuBar {
                background-color: #e0e0e0;
                border-bottom: 1px solid #a0a0a0;
            }
            QMenuBar::item:selected {
                background-color: #c0c0c0;
            }
        """

    @staticmethod
    def dark_theme():
        """Тёмная тема"""
        return """
            QMainWindow, QDialog, QWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 10px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QLineEdit {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
                color: #e0e0e0;
            }
            QCheckBox {
                spacing: 5px;
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                border: 1px solid #555555;
                background-color: #3a3a3a;
            }
            QComboBox {
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
                background-color: #3a3a3a;
                color: #e0e0e0;
            }
            QComboBox QAbstractItemView {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555555;
            }
            QLabel {
                color: #e0e0e0;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QMenuBar {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border-bottom: 1px solid #555555;
            }
            QMenuBar::item:selected {
                background-color: #555555;
            }
            QMenu {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #555555;
            }
        """

    @staticmethod
    def green_theme():
        """Тёмная тема с зелёным акцентом"""
        return """
            QMainWindow, QDialog, QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #2d5d2d;
                border: 1px solid #3a7a3a;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3a7a3a;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3a7a3a;
                border-radius: 3px;
                padding: 3px;
                color: #e0e0e0;
            }
            QCheckBox {
                spacing: 5px;
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                border: 1px solid #3a7a3a;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #2d5d2d;
            }
            QComboBox {
                border: 1px solid #3a7a3a;
                border-radius: 3px;
                padding: 3px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3a7a3a;
            }
            QLabel {
                color: #e0e0e0;
            }
            QProgressBar {
                border: 1px solid #3a7a3a;
                border-radius: 3px;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QMenuBar {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border-bottom: 1px solid #3a7a3a;
            }
            QMenuBar::item:selected {
                background-color: #2d5d2d;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3a7a3a;
            }
            QMenu::item:selected {
                background-color: #2d5d2d;
            }
        """
    @staticmethod
    def get_dialog_styles():
        """Дополнительные стили для диалоговых окон"""
        return """
            QDialog {
                background-color: inherit;
            }
            QProgressBar {
                border: 1px solid #a0a0a0;
                border-radius: 4px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                border-radius: 4px;
            }
        """

    @staticmethod
    def get_theme(name):
        if name == "system":
            # Автоматическое определение системной темы
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                bg_color = app.palette().window().color()
                if bg_color.lightness() > 128:
                    return Themes.light_theme()
                else:
                    return Themes.dark_theme()
            return Themes.light_theme()  # По умолчанию
        elif name == "dark":
            return Themes.dark_theme()
        elif name == "green":
            return Themes.green_theme()
        else:  # "light" or default
            return Themes.light_theme()