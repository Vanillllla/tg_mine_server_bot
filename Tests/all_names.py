from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main_window.ui', self)

        # Выводим все атрибуты, которые начинаются с 'action'
        print("Все actions в окне:")
        for attr_name in dir(self):
            if attr_name.startswith('action'):
                print(f"  - {attr_name}")



p = MainWindow()