from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

        # Будем хранить ссылку на второе окно
        self.second_window = None

    def initUI(self):
        self.setWindowTitle("Главное окно")
        self.setGeometry(100, 100, 800, 600)

        # СОЗДАЕМ МЕНЮБАР
        menubar = self.menuBar()

        # СОЗДАЕМ МЕНЮ "ФАЙЛ"
        file_menu = menubar.addMenu("Файл")  # Это меню "Файл" в верхней панели

        # СОЗДАЕМ ДЕЙСТВИЕ (QAction) ДЛЯ ОТКРЫТИЯ ВТОРОГО ОКНА
        open_second_window_action = QAction("Открыть загрузку", self)

        # Назначаем горячую клавишу (опционально)
        open_second_window_action.setShortcut("Ctrl+O")

        # Добавляем иконку (опционально)
        open_second_window_action.setIcon(QIcon.fromTheme("document-open"))

        # ПОДКЛЮЧАЕМ СИГНАЛ triggered К НАШЕМУ МЕТОДУ
        open_second_window_action.triggered.connect(self.open_second_window)

        # ДОБАВЛЯЕМ ЭТО ДЕЙСТВИЕ В МЕНЮ "ФАЙЛ"
        file_menu.addAction(open_second_window_action)

        # Добавляем разделитель (опционально)
        file_menu.addSeparator()

        # Добавляем действие "Выход" (пример)
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Создаем центральный виджет с информацией
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        label = QLabel("Нажмите 'Файл' в меню и выберите 'Открыть загрузку'")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        central_widget.setLayout(layout)

    def open_second_window(self):
        """Метод, который вызывается при нажатии на пункт меню"""
        # Импортируем здесь, чтобы избежать циклических импортов
        from second_window import SecondWindow

        if self.second_window is None or not self.second_window.isVisible():
            self.second_window = SecondWindow()
            # Если хотим, чтобы второе окно было модальным (блокирует главное)
            # self.second_window.exec_()
            # Если хотим немодальное окно:
            self.second_window.show()
        else:
            # Если окно уже открыто, поднимаем его наверх
            self.second_window.raise_()
            self.second_window.activateWindow()