import json

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.core.dirs_manager import DirsManager
from app.core.paths import config_path, icon_path
from app.gui.i18n import normalize_language, t


class CoresListWindow(QDialog):
    coresChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = DirsManager()
        self.settings_path = config_path("program_settings.json")
        self.cores_path = config_path("cores.json")

        with self.settings_path.open("r", encoding="utf-8") as file:
            self.settings = json.load(file)
        self.settings.setdefault("language", "ru")
        self.language = normalize_language(self.settings.get("language", "ru"))

        self.setWindowIcon(QIcon(icon_path("icon.ico")))
        self.resize(640, 420)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.apply_localization()
        self.load_cores()

    def apply_localization(self):
        lang = self.language
        self.setWindowTitle(t(lang, "cores_list_title"))
        self.table.setHorizontalHeaderLabels(
            [
                t(lang, "cores_list_col_name"),
                t(lang, "cores_list_col_version"),
                t(lang, "cores_list_col_delete"),
            ]
        )

    def load_cores(self):
        with self.cores_path.open("r", encoding="utf-8") as file:
            cores = json.load(file)

        core_items = list(cores.items())
        self.table.setRowCount(len(core_items))

        for row_index, (core_id, core_info) in enumerate(core_items):
            name_item = QTableWidgetItem(str(core_info.get("name", "")))
            version_item = QTableWidgetItem(str(core_info.get("minecraft_version", "")))
            version_item.setTextAlignment(Qt.AlignCenter)

            delete_button = QPushButton(t(self.language, "cores_list_delete"), self.table)
            delete_button.setStyleSheet(
                "QPushButton { background-color: #d64545; color: #ffffff; border: 1px solid #d64545; }"
                "QPushButton:hover { background-color: #b93535; border-color: #b93535; }"
                "QPushButton:pressed { background-color: #962a2a; border-color: #962a2a; }"
            )
            delete_button.clicked.connect(
                lambda _checked=False, cid=str(core_id), cname=str(core_info.get("name", "")): self.delete_core(cid, cname)
            )

            self.table.setItem(row_index, 0, name_item)
            self.table.setItem(row_index, 1, version_item)
            self.table.setCellWidget(row_index, 2, delete_button)

    def delete_core(self, core_id: str, core_name: str):
        reply = QMessageBox.question(
            self,
            t(self.language, "cores_list_delete_confirm_title"),
            t(self.language, "cores_list_delete_confirm_message", core_name=core_name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        if not self.manager.delete_core(core_id):
            QMessageBox.warning(self, t(self.language, "error_title"), t(self.language, "cores_list_delete_failed"))
            return

        self.coresChanged.emit(str(core_id))
        self.load_cores()


__all__ = ["CoresListWindow"]
