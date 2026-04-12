from typing import Dict, Any

from PyQt5 import uic
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtWidgets import QDialog, QMessageBox

from app.core.paths import icon_path, ui_path
from app.core.properties_customizer import PropertiesCustomizer
from app.gui.i18n import normalize_language, t


class ServerSettingsWindow(QDialog):
    def __init__(self, parent=None, core_id: str = ""):
        super().__init__(parent)
        self.core_id = str(core_id or "")
        self.language = normalize_language(getattr(parent, "language", "ru"))
        self.customizer = PropertiesCustomizer()
        uic.loadUi(ui_path("server_settings_ui.ui"), self)
        self.setWindowIcon(QIcon(icon_path("icon.ico")))

        self._difficulty_options = [
            ("peaceful", "server_settings_difficulty_peaceful"),
            ("easy", "server_settings_difficulty_easy"),
            ("normal", "server_settings_difficulty_normal"),
            ("hard", "server_settings_difficulty_hard"),
        ]

        self._wire_signals()
        self._populate_difficulty()
        self.apply_localization()

        try:
            self.load_properties()
            self._show_status(t(self.language, "server_settings_status_idle"))
        except Exception as exc:
            self._show_error(exc)
            self._show_status(t(self.language, "server_settings_status_error"))

    def _wire_signals(self):
        self.saveButton.clicked.connect(self.save)
        self.cancelButton.clicked.connect(self.close)
        self.serverPortConfirmButton.clicked.connect(self.confirm_port)
        self.motdConfirmButton.clicked.connect(self.confirm_motd)
        self.openPropertiesButton.clicked.connect(self.open_properties_file)

    def _populate_difficulty(self):
        self.difficultyComboBox.clear()
        for value, _ in self._difficulty_options:
            self.difficultyComboBox.addItem(value, value)

    def apply_localization(self):
        lang = self.language
        self.setWindowTitle(t(lang, "server_settings_title"))
        self.titleLabel.setText(t(lang, "server_settings_header"))
        self.gameGroupBox.setTitle(t(lang, "server_settings_group_game"))
        self.serverGroupBox.setTitle(t(lang, "server_settings_group_server"))

        self.pvpCheckBox.setText(t(lang, "server_settings_pvp"))
        self.commandBlockCheckBox.setText(t(lang, "server_settings_command_block"))
        self.spawnMonstersCheckBox.setText(t(lang, "server_settings_spawn_monsters"))
        self.maxPlayersLabel.setText(t(lang, "server_settings_max_players"))
        self.entityBroadcastLabel.setText(t(lang, "server_settings_entity_broadcast"))
        self.difficultyLabel.setText(t(lang, "server_settings_difficulty"))

        # rebuild difficulty with localized labels
        current_value = self.difficultyComboBox.currentData()
        self.difficultyComboBox.clear()
        for value, text_key in self._difficulty_options:
            self.difficultyComboBox.addItem(t(lang, text_key), value)
        if current_value:
            index = self.difficultyComboBox.findData(current_value)
            if index >= 0:
                self.difficultyComboBox.setCurrentIndex(index)

        self.onlineModeCheckBox.setText(t(lang, "server_settings_online_mode"))
        self.viewDistanceLabel.setText(t(lang, "server_settings_view_distance"))
        self.serverPortLabel.setText(t(lang, "server_settings_server_port"))
        self.serverPortLineEdit.setPlaceholderText("25565")
        self.serverPortConfirmButton.setText(t(lang, "server_settings_confirm"))
        self.motdLabel.setText(t(lang, "server_settings_motd"))
        self.motdConfirmButton.setText(t(lang, "server_settings_confirm"))

        self.openPropertiesButton.setText(t(lang, "server_settings_open_properties"))
        self.saveButton.setText(t(lang, "server_settings_save"))
        self.cancelButton.setText(t(lang, "server_settings_cancel"))

    def load_properties(self):
        if not self.core_id:
            raise ValueError("active_core_not_selected")

        props = self.customizer.get_properties(self.core_id)

        def get_bool(name: str, default=False):
            value = str(props.get(name, default)).strip().lower()
            return value in ("true", "1", "yes", "on")

        def get_int(name: str, default: int):
            try:
                return max(1, int(str(props.get(name, default)).strip()))
            except Exception:
                return default

        self.pvpCheckBox.setChecked(get_bool("pvp", True))
        self.commandBlockCheckBox.setChecked(get_bool("enable-command-block", False))
        self.spawnMonstersCheckBox.setChecked(get_bool("spawn-monsters", True))
        self.maxPlayersSpinBox.setValue(get_int("max-players", 20))
        self.entityBroadcastSpinBox.setValue(get_int("entity-broadcast-range-percentage", 100))

        difficulty_value = props.get("difficulty", "easy")
        difficulty_value = self._normalize_difficulty_value(str(difficulty_value))
        diff_index = self.difficultyComboBox.findData(difficulty_value)
        if diff_index == -1:
            self.difficultyComboBox.addItem(difficulty_value, difficulty_value)
            diff_index = self.difficultyComboBox.findData(difficulty_value)
        self.difficultyComboBox.setCurrentIndex(max(0, diff_index))

        self.onlineModeCheckBox.setChecked(get_bool("online-mode", True))
        self.viewDistanceSpinBox.setValue(get_int("view-distance", 10))
        self.serverPortLineEdit.setText(str(get_int("server-port", 25565)))
        motd_value = props.get("motd", "")
        self.motdPlainTextEdit.setPlainText(motd_value.replace("\\n", "\n"))

    @staticmethod
    def _normalize_difficulty_value(value: str) -> str:
        mapping = {"0": "peaceful", "1": "easy", "2": "normal", "3": "hard"}
        lower = value.lower()
        return mapping.get(lower, lower)

    def _collect_values(self) -> Dict[str, Any]:
        try:
            port = self._validate_port()
        except ValueError as exc:
            self._show_error(exc)
            raise

        values = {
            "pvp": "true" if self.pvpCheckBox.isChecked() else "false",
            "enable-command-block": "true" if self.commandBlockCheckBox.isChecked() else "false",
            "spawn-monsters": "true" if self.spawnMonstersCheckBox.isChecked() else "false",
            "max-players": self.maxPlayersSpinBox.value(),
            "entity-broadcast-range-percentage": self.entityBroadcastSpinBox.value(),
            "difficulty": self.difficultyComboBox.currentData() or "easy",
            "online-mode": "true" if self.onlineModeCheckBox.isChecked() else "false",
            "view-distance": self.viewDistanceSpinBox.value(),
            "server-port": port,
            "motd": self.motdPlainTextEdit.toPlainText().replace("\n", "\\n"),
        }
        return values

    def save(self):
        try:
            values = self._collect_values()
            self.customizer.set_properties(self.core_id, values)
            self._show_status(t(self.language, "server_settings_status_saved"))
            self.accept()
        except Exception as exc:
            self._show_error(exc)
            self._show_status(t(self.language, "server_settings_status_error"))

    def confirm_port(self):
        try:
            self._validate_port()
            self._show_status(t(self.language, "server_settings_port_ok"))
        except Exception as exc:
            self._show_error(exc)
            self._show_status(t(self.language, "server_settings_status_error"))

    def confirm_motd(self):
        text = self.motdPlainTextEdit.toPlainText()
        if "\n" in text.strip() or text.strip():
            self._show_status(t(self.language, "server_settings_motd_ok"))
        else:
            self._show_status(t(self.language, "server_settings_status_idle"))

    def _validate_port(self) -> int:
        text = self.serverPortLineEdit.text().strip()
        if not text:
            raise ValueError(t(self.language, "server_settings_port_invalid"))
        try:
            port = int(text)
        except ValueError:
            raise ValueError(t(self.language, "server_settings_port_invalid"))
        if port <= 0 or port > 65535:
            raise ValueError(t(self.language, "server_settings_port_invalid"))
        return port

    def _show_error(self, exc: Exception):
        raw = str(exc)
        known_keys = {
            "active_core_not_selected",
            "active_core_not_found_in_cores",
            "active_core_folder_not_set",
        }
        if raw in known_keys:
            message = t(self.language, raw)
        elif isinstance(exc, FileNotFoundError) and "server_properties_not_found" in raw:
            message = t(self.language, "server_settings_properties_missing")
        else:
            message = raw
        QMessageBox.warning(
            self,
            t(self.language, "error_title"),
            message,
        )

    def _show_status(self, message: str):
        if hasattr(self, "statusLabel"):
            self.statusLabel.setText(message)

    def open_properties_file(self):
        try:
            path = self.customizer.get_properties_path(self.core_id)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            self._show_error(exc)
