import json

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
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
        self.theme_name = self._resolve_theme_name(self.settings.get("theme", "light"))

        self.setWindowIcon(QIcon(icon_path("icon.ico")))
        self.resize(640, 420)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 135)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.apply_theme()
        self.apply_localization()
        self.load_cores()

    def _resolve_theme_name(self, theme_name: str) -> str:
        if theme_name != "system":
            return theme_name

        app = QApplication.instance()
        if app:
            bg_color = app.palette().window().color()
            return "light" if bg_color.lightness() > 128 else "dark"
        return "light"

    def apply_theme(self):
        theme_colors = {
            "light": {
                "table_bg": "#ffffff",
                "table_text": "#1f2328",
                "header_bg": "#e9edf2",
                "header_text": "#1f2328",
                "divider": "#aeb4bd",
                "delete_bg": "#d64545",
                "delete_hover": "#b93535",
                "delete_pressed": "#962a2a",
                "delete_text": "#ffffff",
            },
            "dark": {
                "table_bg": "#212830",
                "table_text": "#e6edf3",
                "header_bg": "#252b32",
                "header_text": "#f0f6fc",
                "divider": "#4f5a68",
                "delete_bg": "#c54444",
                "delete_hover": "#b03b3b",
                "delete_pressed": "#8f2f2f",
                "delete_text": "#f8fbff",
            },
            "green": {
                "table_bg": "#0a1714",
                "table_text": "#dff7ee",
                "header_bg": "#112923",
                "header_text": "#b9f5dd",
                "divider": "#245748",
                "delete_bg": "#9b3434",
                "delete_hover": "#862d2d",
                "delete_pressed": "#6f2525",
                "delete_text": "#f4fff0",
            },
        }
        colors = theme_colors.get(self.theme_name, theme_colors["light"])
        divider_width = 2  # +1px to default 1px separators

        self.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: {colors['table_bg']};
                color: {colors['table_text']};
                border: {divider_width}px solid {colors['divider']};
                gridline-color: {colors['divider']};
            }}
            QTableWidget::item {{
                border-right: {divider_width}px solid {colors['divider']};
                border-bottom: {divider_width}px solid {colors['divider']};
                padding: 4px 6px;
            }}
            QHeaderView::section {{
                background-color: {colors['header_bg']};
                color: {colors['header_text']};
                border: 0px;
                border-right: {divider_width}px solid {colors['divider']};
                border-bottom: {divider_width}px solid {colors['divider']};
                padding: 5px 6px;
                font-weight: 600;
            }}
            QTableCornerButton::section {{
                background-color: {colors['header_bg']};
                border: 0px;
                border-right: {divider_width}px solid {colors['divider']};
                border-bottom: {divider_width}px solid {colors['divider']};
            }}
            QPushButton#deleteCoreButton {{
                background-color: {colors['delete_bg']};
                color: {colors['delete_text']};
                border: 1px solid {colors['delete_bg']};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton#deleteCoreButton:hover {{
                background-color: {colors['delete_hover']};
                border-color: {colors['delete_hover']};
            }}
            QPushButton#deleteCoreButton:pressed {{
                background-color: {colors['delete_pressed']};
                border-color: {colors['delete_pressed']};
            }}
            """
        )

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
            delete_button.setObjectName("deleteCoreButton")
            delete_button.clicked.connect(
                lambda _checked=False, cid=str(core_id), cname=str(core_info.get("name", "")): self.delete_core(cid, cname)
            )

            self.table.setItem(row_index, 0, name_item)
            self.table.setItem(row_index, 1, version_item)
            self.table.setCellWidget(row_index, 2, delete_button)
            self.table.setRowHeight(row_index, 40)

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
