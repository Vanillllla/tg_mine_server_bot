import json
import os
import sys
import threading

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt5 import uic
from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QMessageBox, QSystemTrayIcon

from app.core.dirs_manager import DirsManager
from app.core.paths import config_path, icon_path, ui_path
from app.gui.settings_window import SettingsWindow
from app.gui.themes import Themes
from app.gui.upload_window import UploadWindow


class MyApp(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.upload_window = None
        self.settings_window = None
        self.manager = DirsManager()
        self.conn = conn
        uic.loadUi(ui_path("main_ui.ui"), self)
        self.setWindowTitle("Servers Telegram controller")
        self.setWindowIcon(QIcon(icon_path("icon.ico")))

        self.settings_file = config_path("program_settings.json")
        with self.settings_file.open("r", encoding="utf-8") as file:
            self.settings = json.load(file)

        self.apply_theme()
        self.auto_start_last_core_action.setChecked(self.settings["use_last_active_core"])

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path("icon_tray.ico")))
        traymenu = QMenu()
        traymenu.addAction("Open").triggered.connect(self.show)
        traymenu.addAction("Exit").triggered.connect(self.close_program)
        self.tray_icon.setContextMenu(traymenu)

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_server_status)
        self.status_timer.timeout.connect(self.update_bot_status)
        self.status_timer.start(5000)
        self.bot_indicator(False)

        self.startServerButton.setText("START")
        self.startServerButton.setStyleSheet("color: #00CC00;")

        self.coreSelectBox.currentIndexChanged.connect(self.on_core_selected)
        self.load_cores_to_combobox()
        self.startServerButton.clicked.connect(self.start_server)
        self.upload_core_action.triggered.connect(self.open_upload_cores_window)
        self.open_setings_action.triggered.connect(self.open_settings_window)
        self.auto_start_last_core_action.triggered.connect(self.auto_start_last_core)
        self.exit_action.triggered.connect(self.close_program)
        self.to_trey_action.triggered.connect(self.close)
        self.restart_action.triggered.connect(self.restart_program)
        self.action_GitHub.triggered.connect(self.open_github)
        self.bot_control_button.clicked.connect(self.start_bot)

        threading.Thread(target=self.pipe_read, daemon=True).start()
        self.tray_icon.show()
        self.show()

    def pipe_read(self):
        while True:
            msg = self.conn.recv()
            if msg["command"] == "set_bot_status":
                self.bot_indicator(msg["data"])
            elif msg["command"] == "set_server_status":
                self.show_server_status(msg["data"])
            elif msg["command"] == "error_out":
                self.error_output(msg)

    def error_output(self, msg):
        QMessageBox.warning(self, "Error!", f"Error from {msg['from_process']}; Error code : {msg['data']}")

    def auto_start_last_core(self):
        self.settings["use_last_active_core"] = bool(self.auto_start_last_core_action.isChecked())
        self.show_server_status(True)
        with self.settings_file.open("w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=4, ensure_ascii=False)

    def bot_indicator(self, is_active):
        if is_active:
            self.botStatusLabel_ind.setText("         ON")
            self.botStatusLabel_ind.setStyleSheet(
                "background-color: rgba(0, 255, 0, 0.2); color: rgba(0, 255, 0, 0.9);"
            )
        else:
            self.botStatusLabel_ind.setText("         OFF")
            self.botStatusLabel_ind.setStyleSheet(
                "background-color: rgba(255, 0, 0, 0.2);color: rgba(255, 0, 0, 0.9);"
            )

    def update_server_status(self):
        self.conn.send({"to_process": "server", "from_process": "gui", "command": "get_server_status", "data": ""})

    def update_bot_status(self):
        self.conn.send({"to_process": "connector", "from_process": "gui", "command": "get_bot_status", "data": ""})

    def show_server_status(self, is_active):
        if is_active:
            self.startServerButton.setText("STOP")
            self.startServerButton.setStyleSheet("color: #CC0000;")
        else:
            self.startServerButton.setText("START")
            self.startServerButton.setStyleSheet("color: #00CC00;")

    def start_server(self):
        self.conn.send({"to_process": "server", "from_process": "gui", "command": "set_server_status", "data": True})

    def load_cores_to_combobox(self):
        self.coreSelectBox.clear()
        self.coreSelectBox.addItem("Выберите ядро")
        with config_path("cores.json").open("r", encoding="utf-8") as file:
            core_list = json.load(file)

        for core_id, core in core_list.items():
            self.coreSelectBox.addItem(f"{core_id}_{core['name']}")
            if self.settings["use_last_active_core"] and str(core_id) == self.settings["active_core"]:
                self.coreSelectBox.setCurrentIndex(int(core_id))

        if not self.settings["use_last_active_core"]:
            self.settings["active_core"] = ""

        with self.settings_file.open("w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=4, ensure_ascii=False)

    def on_core_selected(self, index):
        if index > 0:
            selected_core = self.coreSelectBox.currentText()
            core_id = self.manager.core_available(selected_core)
            self.coreLabel.setText(selected_core)
            self.versionLabel.setText("Появится позже :3")
            self.settings["active_core"] = core_id
            with self.settings_file.open("w", encoding="utf-8") as file:
                json.dump(self.settings, file, indent=4, ensure_ascii=False)

    def apply_theme(self):
        theme_name = self.settings.get("theme", "light")
        stylesheet = Themes.get_theme(theme_name)
        QApplication.instance().setStyleSheet(stylesheet)

    def start_bot(self):
        self.pipe_send({"to_process": "connector", "from_process": "ui", "command": "bot_switch", "data": None})

    def pipe_send(self, msg: dict):
        if self.conn:
            self.conn.send(msg)

    def open_upload_cores_window(self):
        self.upload_window = UploadWindow(self, "downloads_cores")
        self.upload_window.exec_()
        self.apply_theme()
        self.load_cores_to_combobox()

    def open_settings_window(self):
        self.settings_window = SettingsWindow(self)
        self.settings_window.settingsChanged.connect(self.load_settings)
        self.settings_window.exec_()

    def load_settings(self):
        with self.settings_file.open("r", encoding="utf-8") as file:
            self.settings = json.load(file)

    def open_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/Vanillllla/tg_mine_server_bot"))

    def restart_program(self):
        QMessageBox.warning(
            self,
            "Перезагрузка",
            "Приложение очень хотело перезагрузиться само, но у него лапки! :3 \nПерезапустите его сами!",
        )

    def close_program(self):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите выйти?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.pipe_send({"to_process": "connector", "from_process": "ui", "command": "exit", "data": None})
            QApplication.quit()

    def closeEvent(self, event):
        self.hide()
        self.tray_icon.show()
        event.ignore()
        QApplication.quit()
        self.pipe_send({"to_process": "connector", "from_process": "ui", "command": "exit", "data": None})


def run(conn):
    app = QApplication(sys.argv)
    MyApp(conn)
    sys.exit(app.exec_())
