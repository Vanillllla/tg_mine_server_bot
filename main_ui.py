import os
import json
import threading
import sys
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QMessageBox
from PyQt5.QtWidgets import QMainWindow, QLabel
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtCore import QUrl, QTimer

from upload_window import UploadWindow
from settings_window import SettingsWindow
from thems_my import Themes

class MyApp(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.upload_window = None
        self.settings_window = None
        self.conn = conn
        uic.loadUi('main_ui.ui', self)
        self.setWindowTitle("Servers Telegram controller")
        self.setWindowIcon(QIcon('icon.ico'))

        with open('program_settings.json', 'r', encoding='utf-8') as f:
            self.settings = json.load(f)

        self.apply_theme()
        self.auto_start_last_core_action.setChecked(self.settings['use_last_active_core'])
        self.auto_start_last_core_action.triggered.connect(self.auto_start_last_core)

        ############################################################################### далее монтируем трей
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon_tray.ico"))  # или QIcon.fromTheme()
        traymenu = QMenu()
        traymenu.addAction("Open").triggered.connect(self.show)
        traymenu.addAction("Exit").triggered.connect(self.close_program)
        self.tray_icon.setContextMenu(traymenu)
        ############################################################################### далее таймеры опросов

        # self.status_timer = QTimer()
        # self.status_timer.timeout.connect(self.update_status)
        #
        # self.status_timer.start(2000)
        self.bot_indicator(False)

        ############################################################################### далее обработчики

        self.coreSelectBox.currentIndexChanged.connect(self.on_core_selected)
        self.load_cores_to_combobox()

        # # Кнопки сервера:
        # self.pushButton.clicked.connect(self.start_server)
        # self.pushButton_2.clicked.connect(self.stop_server)

        self.upload_core_action.triggered.connect(self.open_upload_cores_window)

        self.open_setings_action.triggered.connect(self.open_settings_window)

        self.exit_action.triggered.connect(self.close_program)
        self.to_trey_action.triggered.connect(self.close)
        self.restart_action.triggered.connect(self.restart_program)

        self.action_GitHub.triggered.connect(self.open_github)

        self.bot_control_button.clicked.connect(self.start_bot)

        threading.Thread(
            target=self.pipe_read,
            daemon=True
        ).start()

        self.initUI()

    def pipe_read(self):
        while True:
            msg = self.conn.recv()
            if msg["command"] == "set_bot_status":
                self.bot_indicator(msg["data"])

    def initUI(self):
        self.tray_icon.show()
        self.show()

    def auto_start_last_core(self):
        self.settings["auto_start_last_core"] = self.auto_start_last_core_action.isChecked()
        print("Тут проблема, ее нужно решить!!!")
        # with open('program_settings.json', 'w', encoding='utf-8') as f:
        #     json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def bot_indicator(self, is_active):
        if is_active:
            self.botStatusLabel_ind.setText("         ON")
            self.botStatusLabel_ind.setStyleSheet("background-color: rgba(0, 255, 0, 0.2); color: rgba(0, 255, 0, 0.9);")
        else:
            self.botStatusLabel_ind.setText("         OFF")
            self.botStatusLabel_ind.setStyleSheet("background-color: rgba(255, 0, 0, 0.2);color: rgba(255, 0, 0, 0.9);")

    def load_cores_to_combobox(self):
        """Загружает список ядер из папки downloads_cores в комбобокс"""
        cores_path = self.settings.get("cores_path", "downloads_cores")
        if not os.path.exists(cores_path):
            os.makedirs(cores_path)
        self.coreSelectBox.clear()
        self.coreSelectBox.addItem("Выберите ядро")
        jar_files = []
        try:
            for file in os.listdir(cores_path):
                if file.endswith('.jar'):
                    jar_files.append(file)
        except Exception as e:
            print(f"Ошибка чтения папки с ядрами: {e}")
        for jar in sorted(jar_files):
            self.coreSelectBox.addItem(jar)
        # Если есть активное ядро в cores.json, выбираем его
        with open('program_settings.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
        if settings["use_last_active_core"] == True:
            try:
                with open('cores.json', 'r', encoding='utf-8') as f:
                    cores_data = json.load(f)
                    active_core = cores_data.get('active_core', {}).get('core_name', '')
                    if active_core:
                        index = self.coreSelectBox.findText(active_core)
                        if index >= 0:
                            self.coreSelectBox.setCurrentIndex(index)
            except Exception as e:
                print(f"Ошибка чтения cores.json: {e}")

    def on_core_selected(self, index):
        """Обработчик выбора ядра из комбобокса"""
        if index > 0:  # Пропускаем первый элемент "Выберите ядро"
            selected_core = self.coreSelectBox.currentText()
            print(f"Выбрано ядро: {selected_core}")

            self.coreLabel.setText(selected_core)
            self.versionLabel.setText("Появится позже :3")  # Здесь можно парсить версию из имени



    def printsettings(self):
        print(self.settings)

    def apply_theme(self):
        """Применяет текущую тему ко всему приложению"""
        theme_name = self.settings.get("theme", "light")
        stylesheet = Themes.get_theme(theme_name)
        app = QApplication.instance()
        app.setStyleSheet(stylesheet)

    def start_bot(self):
        request = {"to_process": "connector", "command": "bot_switch", "data": None}
        self.pipe_send(request)

    def pipe_send(self, msg: dict):
        if self.conn:
            self.conn.send(msg)

    def open_upload_cores_window(self ):
        """Открываем окно загрузки файлов"""
        self.upload_window = UploadWindow(self, "downloads_cores")  # self как родитель
        self.upload_window.exec_()
        self.apply_theme()
        self.load_cores_to_combobox()

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
        # QApplication.quit()
        # self.pipe_send({"to_process": "connector", "command": "restart", "data": None})
        # os.execl(sys.executable, sys.executable, *sys.argv)
        QMessageBox.warning(
            self,"Перезагрузка",
            "Приложение очень хотело перезагрузиться само, но у него лапки! :3 \n"
            "Перезапустите его сами!"
        )


    def close_program(self):
        reply = QMessageBox.question(
            self, 'Подтверждение',
            'Вы уверены, что хотите выйти?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            request = {"to_process": "connector", "command": "exit", "data": None}
            self.pipe_send(request)
            QApplication.quit()   # Закрыть

    def closeEvent(self, event):



        self.hide()  # Скрываем окно
        self.tray_icon.show()  # Показываем иконку в трее
        event.ignore()  # Не закрываем программу

        ### ЗАКОМЕНТИТЬ ТО ЧТО НИЖЕ В ЭТОЙ ФУНКЦИИ
        QApplication.quit()  # Закрыть
        request = {"to_process": "connector", "command": "exit", "data": None}
        self.pipe_send(request)





def run(conn):
    app = QApplication(sys.argv)
    ex = MyApp(conn)
    sys.exit(app.exec_())
