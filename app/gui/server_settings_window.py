import json
from typing import Dict

from PyQt5 import uic
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt5.Qt import QDesktopServices

from app.core.paths import config_path, icon_path, ui_path
from app.core.properties_customizer import PropertiesCustomizer
from app.gui.i18n import normalize_language, t


class ServerSettingsWindow(QDialog):
    def __init__(self, parent=None, core_id: str = None):
        super().__init__(parent)
        self.settings_file = config_path("program_settings.json")
        self.cores_file = config_path("cores.json")

        uic.loadUi(ui_path("server_settings_ui.ui"), self)
        self.setWindowIcon(QIcon(icon_path("icon.ico")))

        with self.settings_file.open("r", encoding="utf-8") as file:
            self.settings = json.load(file)
        self.settings.setdefault("language", "ru")
        self.language = normalize_language(self.settings.get("language", "ru"))

        with self.cores_file.open("r", encoding="utf-8") as file:
            self.cores = json.load(file)

        self.active_core = str(core_id) if core_id else str(self.settings.get("active_core", ""))
        self.properties: Dict[str, str] = {}

        self.cancelButton.clicked.connect(self.reject)
        self.saveButton.clicked.connect(self.save)
        self.openPropertiesButton.clicked.connect(self.open_properties_file)

        self.apply_localization()
        self.load_values()

    def apply_localization(self):
        lang = self.language
        self.setWindowTitle(t(lang, "server_settings_title"))
        self.headerLabel.setText(t(lang, "server_settings_title"))

        self.gameGroupBox.setTitle(t(lang, "server_settings_game"))
        self.serverGroupBox.setTitle(t(lang, "server_settings_server"))

        self.pvpCheckBox.setText(t(lang, "server_pvp"))
        self.commandBlockCheckBox.setText(t(lang, "server_command_block"))
        self.spawnMonstersCheckBox.setText(t(lang, "server_spawn_monsters"))
        self.maxPlayersLabel.setText(t(lang, "server_max_players"))
        self.broadcastLabel.setText(t(lang, "server_entity_broadcast"))
        self.difficultyLabel.setText(t(lang, "server_difficulty"))

        self.onlineModeCheckBox.setText(t(lang, "server_online_mode"))
        self.viewDistanceLabel.setText(t(lang, "server_view_distance"))
        self.portLabel.setText(t(lang, "server_port"))
        self.motdLabel.setText(t(lang, "server_motd"))
        self.xmsLabel.setText(t(lang, "server_memory_min"))
        self.xmxLabel.setText(t(lang, "server_memory_max"))

        self.openPropertiesButton.setText(t(lang, "server_open_properties"))
        self.saveButton.setText(t(lang, "settings_save"))
        self.cancelButton.setText(t(lang, "settings_cancel"))

    def load_values(self):
        if not self.active_core:
            QMessageBox.warning(self, t(self.language, "error_title"), t(self.language, "core_not_selected"))
            self.reject()
            return

        try:
            self.properties = PropertiesCustomizer.get_properties(self.active_core)
        except Exception as exc:
            QMessageBox.warning(self, t(self.language, "error_title"), str(exc))
            self.reject()
            return

        def to_bool(key: str, default=False):
            val = self.properties.get(key, str(default))
            return str(val).lower() == "true"

        def to_int(key: str, default=""):
            return self.properties.get(key, default)

        self.pvpCheckBox.setChecked(to_bool("pvp", True))
        self.commandBlockCheckBox.setChecked(to_bool("enable-command-block", False))
        self.spawnMonstersCheckBox.setChecked(to_bool("spawn-monsters", True))
        self.maxPlayersLineEdit.setText(str(to_int("max-players", "")))
        self.broadcastLineEdit.setText(str(to_int("entity-broadcast-range-percentage", "")))

        difficulty = self.properties.get("difficulty", "easy")
        idx = self.difficultyComboBox.findText(difficulty)
        self.difficultyComboBox.setCurrentIndex(max(idx, 0))

        self.onlineModeCheckBox.setChecked(to_bool("online-mode", True))
        self.viewDistanceLineEdit.setText(str(to_int("view-distance", "")))
        self.serverPortLineEdit.setText(str(to_int("server-port", "")))
        self.motdTextEdit.setPlainText(self.properties.get("motd", ""))

        # memory from cores.json
        core = self.cores.get(self.active_core, {})
        self._set_memory_field(core.get("xms", 256), self.xmsLineEdit, self.xmsUnitComboBox, core.get("xms_unit"))
        self._set_memory_field(core.get("xmx", 1024), self.xmxLineEdit, self.xmxUnitComboBox, core.get("xmx_unit"))

    @staticmethod
    def _set_memory_field(value, line_edit, unit_combo, unit_hint=None):
        try:
            value = int(value)
        except Exception:
            value = 256
        unit = unit_hint or ("GB" if value % 1024 == 0 and value >= 1024 else "MB")
        display_val = value // 1024 if unit == "GB" else value
        unit_combo.setCurrentText(unit)
        line_edit.setText(str(display_val))

    def _memory_to_mb(self, line_edit, unit_combo, fallback):
        try:
            val = int(line_edit.text())
        except ValueError:
            return fallback
        if val <= 0:
            return fallback
        unit = unit_combo.currentText()
        return val * 1024 if unit == "GB" else val

    def open_properties_file(self):
        try:
            path = PropertiesCustomizer._properties_path(self.active_core)  # type: ignore[attr-defined]
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            QMessageBox.warning(self, t(self.language, "error_title"), str(exc))

    def save(self):
        int_fields = [
            (self.maxPlayersLineEdit, "max-players", 1, 100000),
            (self.broadcastLineEdit, "entity-broadcast-range-percentage", 1, 10000),
            (self.viewDistanceLineEdit, "view-distance", 1, 64),
            (self.serverPortLineEdit, "server-port", 1, 65535),
        ]
        changes: Dict[str, str] = {
            "pvp": "true" if self.pvpCheckBox.isChecked() else "false",
            "enable-command-block": "true" if self.commandBlockCheckBox.isChecked() else "false",
            "spawn-monsters": "true" if self.spawnMonstersCheckBox.isChecked() else "false",
            "online-mode": "true" if self.onlineModeCheckBox.isChecked() else "false",
            "difficulty": self.difficultyComboBox.currentText(),
            "motd": self.motdTextEdit.toPlainText().replace("\r", ""),
        }

        for widget, key, min_v, max_v in int_fields:
            text = widget.text().strip()
            if not text.isdigit():
                QMessageBox.warning(self, t(self.language, "error_title"), t(self.language, "field_should_be_int"))
                return
            value = int(text)
            if value < min_v or value > max_v:
                QMessageBox.warning(self, t(self.language, "error_title"), t(self.language, "field_out_of_range"))
                return
            changes[key] = str(value)

        # memory values to cores.json (MB)
        xms_mb = self._memory_to_mb(self.xmsLineEdit, self.xmsUnitComboBox, 256)
        xmx_mb = self._memory_to_mb(self.xmxLineEdit, self.xmxUnitComboBox, 1024)
        if xmx_mb < xms_mb:
            QMessageBox.warning(self, t(self.language, "error_title"), t(self.language, "memory_invalid"))
            return

        try:
            PropertiesCustomizer.set_properties(self.active_core, changes)
            self._save_memory(xms_mb, xmx_mb)
        except Exception as exc:
            QMessageBox.warning(self, t(self.language, "error_title"), str(exc))
            return

        self.accept()

    def _save_memory(self, xms_mb: int, xmx_mb: int):
        unit_xms = self.xmsUnitComboBox.currentText()
        unit_xmx = self.xmxUnitComboBox.currentText()
        self.cores[str(self.active_core)]["xms"] = xms_mb
        self.cores[str(self.active_core)]["xmx"] = xmx_mb
        self.cores[str(self.active_core)]["xms_unit"] = unit_xms
        self.cores[str(self.active_core)]["xmx_unit"] = unit_xmx
        with self.cores_file.open("w", encoding="utf-8") as file:
            json.dump(self.cores, file, ensure_ascii=False, indent=4)


def run_demo():
    import sys

    app = QApplication(sys.argv)
    w = ServerSettingsWindow()
    w.show()
    sys.exit(app.exec_())


__all__ = ["ServerSettingsWindow"]
