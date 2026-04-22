import json
import os
import sys
import threading
import time
from pathlib import Path

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt5 import uic
from PyQt5.QtCore import QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QMessageBox, QSystemTrayIcon

from app.core.dirs_manager import DirsManager
from app.core.paths import config_path, icon_path, ui_path
from app.gui.cores_list_window import CoresListWindow
from app.gui.i18n import normalize_language, t
from app.gui.server_settings_window import ServerSettingsWindow
from app.gui.settings_window import SettingsWindow
from app.gui.themes import Themes
from app.gui.upload_window import UploadWindow


class MyApp(QMainWindow):
    pipe_message = pyqtSignal(dict)
    def __init__(self, conn):
        super().__init__()
        self.upload_window = None
        self.settings_window = None
        self.server_settings_window = None
        self.cores_list_window = None
        self.manager = DirsManager()
        self.conn = conn
        self.bot_is_active = False
        self.server_is_active = False
        self.server_start_time = None

        uic.loadUi(ui_path("main_ui.ui"), self)
        self.setWindowIcon(QIcon(icon_path("icon.ico")))

        self.settings_file = config_path("program_settings.json")
        with self.settings_file.open("r", encoding="utf-8") as file:
            self.settings = json.load(file)
        self.settings.setdefault("language", "ru")
        self.language = normalize_language(self.settings.get("language", "ru"))

        self.apply_theme()
        self.auto_start_last_core_action.setChecked(self.settings["use_last_active_core"])

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path("icon_tray.ico")))
        traymenu = QMenu()
        self.tray_open_action = traymenu.addAction("")
        traymenu.addSeparator()
        self.tray_toggle_server_action = traymenu.addAction("")
        self.tray_toggle_bot_action = traymenu.addAction("")
        traymenu.addSeparator()
        self.tray_exit_action = traymenu.addAction("")

        self.tray_open_action.triggered.connect(self.show)
        self.tray_toggle_server_action.triggered.connect(self.toggle_server_from_tray)
        self.tray_toggle_bot_action.triggered.connect(self.toggle_bot_from_tray)
        self.tray_exit_action.triggered.connect(self.close_program)
        self.tray_icon.setContextMenu(traymenu)

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_server_status)
        self.status_timer.timeout.connect(self.update_bot_status)
        self.status_timer.start(5000)

        self.load_cores_to_combobox()
        self.coreSelectBox.currentIndexChanged.connect(self.on_core_selected)
        self.startServerButton.clicked.connect(self.start_server)
        self.settingsServerButton.clicked.connect(self.open_server_settings_window)
        self.upload_core_action.triggered.connect(self.open_upload_cores_window)
        self.open_setings_action.triggered.connect(self.open_settings_window)
        self.auto_start_last_core_action.triggered.connect(self.auto_start_last_core)
        self.exit_action.triggered.connect(self.close_program)
        self.to_trey_action.triggered.connect(self.close)
        self.restart_action.triggered.connect(self.restart_program)
        self.action_GitHub.triggered.connect(self.open_github)
        self.bot_control_button.clicked.connect(self.start_bot)
        self.openfolderButton.clicked.connect(self.open_folder)
        self.corelistButton.clicked.connect(self.open_cores_list_window)

        self.console_output.setMaximumBlockCount(3000)
        self.console_input.returnPressed.connect(self.send_server_command)
        self.console_send_button.clicked.connect(self.send_server_command)

        self.online_timer = QTimer()
        self.online_timer.timeout.connect(self.update_online_time)

        self.pipe_message.connect(self.handle_pipe_message)
        threading.Thread(target=self.pipe_read, daemon=True).start()

        # self.load_cores_to_combobox()
        self.bot_indicator(False)
        self.show_server_status(False)
        self.apply_localization()
        self._update_tray_labels()

        self.tray_icon.show()
        self.show()

    def pipe_read(self):
        while True:
            msg = self.conn.recv()
            self.pipe_message.emit(msg)

    def handle_pipe_message(self, msg):
        if msg["command"] == "set_bot_status":
            self.bot_indicator(msg["data"])
        elif msg["command"] == "set_server_status":
            self.show_server_status(msg["data"])
        elif msg["command"] == "set_server_version":
            data = msg.get("data", {})
            active_core = str(self.settings.get("active_core", ""))
            if active_core and str(data.get("core_id", "")) == active_core:
                self.versionLabel.setText(str(data.get("minecraft_version", "")))
        elif msg["command"] == "error_out":
            self.error_output(msg)
        elif msg["command"] == "server_log":
            self.append_server_log(msg)

    def append_server_log(self, msg):
        line = msg.get("data", {}).get("line", "")
        self.console_output.appendPlainText(f"{line}")

    def send_server_command(self):
        command = self.console_input.text().strip()
        if not command:
            return
        self.conn.send({"to_process": "server", "from_process": "gui", "command": "server_command", "data": command})
        self.console_output.appendPlainText(f"> {command}")
        self.console_input.clear()

    def apply_localization(self):
        lang = normalize_language(self.settings.get("language", "ru"))
        self.language = lang

        self.setWindowTitle(t(lang, "app_title"))

        self.menu.setTitle(t(lang, "menu_file"))
        self.menu_2.setTitle(t(lang, "menu_help"))
        self.upload_core_action.setText(t(lang, "menu_add_core"))
        self.auto_start_last_core_action.setText(t(lang, "menu_remember_profile"))
        self.core_select_action.setText(t(lang, "menu_core_select"))
        self.open_setings_action.setText(t(lang, "menu_settings"))
        self.open_setings_console_action.setText(t(lang, "menu_console_settings"))
        self.restart_action.setText(t(lang, "menu_restart"))
        self.to_trey_action.setText(t(lang, "menu_to_tray"))
        self.exit_action.setText(t(lang, "menu_exit"))
        self.action_5.setText(t(lang, "menu_help_item"))
        self.action_GitHub.setText(t(lang, "menu_github"))
        self.tray_open_action.setText(t(lang, "tray_open"))
        self.tray_exit_action.setText(t(lang, "tray_exit"))

        self.botStatusLabel.setText(t(lang, "bot_label"))
        self.bot_control_button.setText(t(lang, "bot_start_button"))

        self.serverGroupBox.setTitle(t(lang, "server_group"))
        self.label.setText(t(lang, "server_core"))
        self.label_2.setText(t(lang, "server_version"))
        self.label_3.setText(t(lang, "server_players"))
        self.label_4.setText(t(lang, "server_online_time"))
        self.settingsServerButton.setText(t(lang, "server_settings"))
        self.openfolderButton.setText(t(lang, "server_open_folder"))
        self.corelistButton.setText(t(lang, "core_list_button"))

        self.consoleGroupBox.setTitle(t(lang, "console_title"))
        self.console_input.setPlaceholderText(t(lang, "console_placeholder"))
        self.console_send_button.setText(t(lang, "console_send"))

        self._update_tray_labels()

        # if self.coreSelectBox.count() > 0:
        #     self.coreSelectBox.setItemText(0, t(lang, "core_select_placeholder"))
        # self._set_version_label(self.settings.get("active_core", ""))

        self.bot_indicator(self.bot_is_active)
        self.show_server_status(self.server_is_active)

    def error_output(self, msg):
        QMessageBox.warning(
            self,
            t(self.language, "error_title"),
            t(self.language, "error_message", source=msg["from_process"], data=msg["data"]),
        )

    def auto_start_last_core(self):
        self.settings["use_last_active_core"] = bool(self.auto_start_last_core_action.isChecked())
        self.show_server_status(True)
        with self.settings_file.open("w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=4, ensure_ascii=False)

    def bot_indicator(self, is_active):
        self.bot_is_active = is_active
        if is_active:
            self.botStatusLabel_ind.setText(t(self.language, "bot_on"))
            self.botStatusLabel_ind.setStyleSheet(
                "background-color: transparent;"
                "color: #8dff77;"
                "border: 1px solid rgba(141, 255, 119, 0.85);"
                "border-radius: 14px;"
                "padding: 0 12px;"
            )
        else:
            self.botStatusLabel_ind.setText(t(self.language, "bot_off"))
            self.botStatusLabel_ind.setStyleSheet(
                "background-color: transparent;"
                "color: #ff7d7d;"
                "border: 1px solid rgba(255, 125, 125, 0.85);"
                "border-radius: 14px;"
                "padding: 0 12px;"
            )
        self._update_tray_labels()

    def update_server_status(self):
        self.conn.send({"to_process": "server", "from_process": "gui", "command": "get_server_status", "data": ""})

    def update_bot_status(self):
        self.conn.send({"to_process": "connector", "from_process": "gui", "command": "get_bot_status", "data": ""})

    def show_server_status(self, is_active):
        previous = self.server_is_active
        self.server_is_active = is_active
        if is_active:
            self.startServerButton.setText(t(self.language, "server_stop"))
            self.startServerButton.setStyleSheet("color: #CC0000;")
            if self.server_start_time is None:
                self.server_start_time = time.time()
            if not self.online_timer.isActive():
                self.online_timer.start(1000)
        else:
            self.startServerButton.setText(t(self.language, "server_start"))
            self.startServerButton.setStyleSheet("color: #00CC00;")
            self.online_timer.stop()
            self.server_start_time = None
            if hasattr(self, "versionLabel_3"):
                self.versionLabel_3.setText(t(self.language, "server_offline_state"))
        self._update_tray_labels()

    def update_online_time(self):
        if self.server_start_time is None:
            return
        elapsed = int(time.time() - self.server_start_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        if hasattr(self, "versionLabel_3"):
            self.versionLabel_3.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def open_folder(self):
        with config_path("cores.json").open("r", encoding="utf-8") as file:
            core_list = json.load(file)

        if self.settings["active_core"] != "":
            path = str(core_list[str(self.settings["active_core"])]["core_folder"])
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.error_output({'from_process': "GUI", "data": 'core_folder_not_selected'})

    def start_server(self):
        if not self.settings.get("active_core"):
            QMessageBox.warning(self, t(self.language, "error_title"), t(self.language, "active_core_not_selected"))
            self.show_server_status(False)
            return
        if self.server_is_active:
            self.conn.send({"to_process": "server", "from_process": "gui", "command": "set_server_status", "data": False})
            self.show_server_status(False)
        else:
            self.conn.send({"to_process": "server", "from_process": "gui", "command": "set_server_status", "data": True})
            self.show_server_status(True)

    def load_cores_to_combobox(self):
        self.coreSelectBox.clear()
        self.coreSelectBox.addItem(t(self.language, "core_select_placeholder"))
        with config_path("cores.json").open("r", encoding="utf-8") as file:
            core_list = json.load(file)

        active_core = str(self.settings.get("active_core", ""))
        selected_index = 0
        for core_id, core_data in core_list.items():
            self.coreSelectBox.addItem(f"{core_id}_{core_data.get('name', '')}")
            if self.settings.get("use_last_active_core") and str(core_id) == active_core:
                selected_index = self.coreSelectBox.count() - 1

        if selected_index > 0:
            self.coreSelectBox.setCurrentIndex(selected_index)
            self._set_version_label(active_core)
        else:
            if not self.settings.get("use_last_active_core") or (active_core and active_core not in core_list):
                self.settings["active_core"] = ""
            if self.settings.get("active_core", "") == "":
                self.versionLabel.setText("")

        with self.settings_file.open("w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=4, ensure_ascii=False)

    def on_core_selected(self, index):
        if index > 0:
            selected_core = self.coreSelectBox.currentText()
            core_id = self.manager.core_available(selected_core)
            self.coreLabel.setText(selected_core)
            self._set_version_label(core_id)
            self.settings["active_core"] = core_id
            with self.settings_file.open("w", encoding="utf-8") as file:
                json.dump(self.settings, file, indent=4, ensure_ascii=False)
        else:
            self.settings["active_core"] = ""
            self.versionLabel.setText("")
            with self.settings_file.open("w", encoding="utf-8") as file:
                json.dump(self.settings, file, indent=4, ensure_ascii=False)

    def apply_theme(self):
        theme_name = self.settings.get("theme", "light")
        stylesheet = Themes.get_theme(theme_name)
        QApplication.instance().setStyleSheet(stylesheet)

    def start_bot(self):
        self.pipe_send({"to_process": "connector", "from_process": "ui", "command": "bot_switch", "data": None})

    def toggle_bot_from_tray(self):
        self.start_bot()

    def toggle_server_from_tray(self):
        self.start_server()

    def pipe_send(self, msg: dict):
        if self.conn:
            self.conn.send(msg)

    def open_upload_cores_window(self):
        self.upload_window = UploadWindow(self, "downloads_cores")
        self.upload_window.exec_()
        self.apply_theme()
        self.apply_localization()
        self.load_cores_to_combobox()

    def open_cores_list_window(self):
        self.cores_list_window = CoresListWindow(self)
        self.cores_list_window.coresChanged.connect(self.on_core_deleted)
        self.cores_list_window.exec_()

    def on_core_deleted(self, core_id: str):
        if str(self.settings.get("active_core", "")) == str(core_id):
            self.settings["active_core"] = ""
            self.coreLabel.setText("")
            self.versionLabel.setText("")
            with self.settings_file.open("w", encoding="utf-8") as file:
                json.dump(self.settings, file, indent=4, ensure_ascii=False)
        self.load_cores_to_combobox()

    def open_server_settings_window(self):
        active_core = self.settings.get("active_core", "")
        if not active_core:
            QMessageBox.warning(self, t(self.language, "error_title"), t(self.language, "active_core_not_selected"))
            return
        self.server_settings_window = ServerSettingsWindow(self, active_core)
        if getattr(self.server_settings_window, "init_failed", False):
            return
        self.server_settings_window.exec_()

    def open_settings_window(self):
        self.settings_window = SettingsWindow(self)
        self.settings_window.settingsChanged.connect(self.load_settings)
        self.settings_window.exec_()

    def load_settings(self):
        with self.settings_file.open("r", encoding="utf-8") as file:
            self.settings = json.load(file)
        self.settings.setdefault("language", "ru")
        self.language = normalize_language(self.settings.get("language", "ru"))
        self.apply_theme()
        self.apply_localization()

    def _set_version_label(self, core_id):
        if not core_id:
            self.versionLabel.setText("")
            return
        try:
            with config_path("cores.json").open("r", encoding="utf-8") as file:
                cores = json.load(file)
            info = cores.get(str(core_id), {})
            version = info.get("minecraft_version", "")
            self.versionLabel.setText(str(version) if version else "")
        except Exception:
            self.versionLabel.setText("")

    def open_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/Vanillllla/tg_mine_server_bot"))

    def restart_program(self):
        QMessageBox.warning(self, t(self.language, "restart_title"), t(self.language, "restart_message"))

    def close_program(self):
        reply = QMessageBox.question(
            self,
            t(self.language, "exit_confirm_title"),
            t(self.language, "exit_confirm_message"),
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
        # QApplication.quit()
        # self.pipe_send({"to_process": "connector", "from_process": "ui", "command": "exit", "data": None})

    def _update_tray_labels(self):
        if hasattr(self, "tray_toggle_server_action"):
            server_text = t(self.language, "tray_server_stop" if self.server_is_active else "tray_server_start")
            bot_text = t(self.language, "tray_bot_stop" if self.bot_is_active else "tray_bot_start")
            self.tray_toggle_server_action.setText(server_text)
            self.tray_toggle_bot_action.setText(bot_text)
        if hasattr(self, "tray_open_action"):
            self.tray_open_action.setText(t(self.language, "tray_open"))
        if hasattr(self, "tray_exit_action"):
            self.tray_exit_action.setText(t(self.language, "tray_exit"))


def run(conn):
    app = QApplication(sys.argv)
    MyApp(conn)
    sys.exit(app.exec_())
