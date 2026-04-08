class Themes:
    @staticmethod
    def _theme_template(colors):
        return f"""
            QMainWindow, QDialog, QWidget {{
                background-color: {colors['window_bg']};
                color: {colors['text']};
                font-size: 10pt;
            }}
            QFrame#frame_2 {{
                background-color: {colors['panel_bg']};
                border: 1px solid {colors['border']};
            }}
            QGroupBox {{
                border: 1px solid {colors['border']};
                background-color: {colors['panel_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: {colors['text']};
                font-weight: 600;
            }}
            QPushButton {{
                background-color: {colors['button_bg']};
                border: 1px solid {colors['border']};
                color: {colors['button_text']};
            }}
            QPushButton:hover {{
                background-color: {colors['button_hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['button_pressed']};
            }}
            QPushButton:disabled {{
                color: {colors['text_muted']};
                border-color: {colors['border_soft']};
            }}
            QLineEdit, QPlainTextEdit, QTextEdit {{
                background-color: {colors['input_bg']};
                border: 1px solid {colors['border']};
                color: {colors['text']};
                selection-background-color: {colors['accent']};
            }}
            QPlainTextEdit#console_output {{
                background-color: {colors['console_bg']};
                border: 1px solid {colors['console_border']};
                color: {colors['text']};
            }}
            QLineEdit#console_input {{
                background-color: {colors['console_input_bg']};
                border: 1px solid {colors['console_border']};
                color: {colors['text']};
            }}
            QPushButton#console_send_button {{
                background-color: {colors['console_button_bg']};
                border: 1px solid {colors['console_border']};
                color: {colors['button_text']};
            }}
            QPushButton#console_send_button:hover {{
                background-color: {colors['console_button_hover']};
            }}
            QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
                border: 1px solid {colors['accent']};
            }}
            QComboBox {{
                border: 1px solid {colors['border']};
                background-color: {colors['input_bg']};
                color: {colors['text']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {colors['input_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                selection-background-color: {colors['accent']};
            }}
            QCheckBox {{
                spacing: 6px;
                color: {colors['text']};
            }}
            QCheckBox::indicator {{
                width: 15px;
                height: 15px;
                border: 1px solid {colors['border']};
                background-color: {colors['input_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['accent']};
            }}
            QLabel {{
                color: {colors['text']};
            }}
            QProgressBar {{
                border: 1px solid {colors['border']};
                text-align: center;
                background-color: {colors['input_bg']};
                color: {colors['text']};
            }}
            QProgressBar::chunk {{
                background-color: {colors['accent']};
            }}
            QMenuBar {{
                background-color: {colors['menu_bg']};
                color: {colors['text']};
                border-bottom: 1px solid {colors['border_soft']};
            }}
            QMenuBar::item {{
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: {colors['menu_hover']};
            }}
            QMenu {{
                background-color: {colors['menu_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 10px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {colors['menu_hover']};
            }}
            QStatusBar {{
                background-color: {colors['menu_bg']};
                border-top: 1px solid {colors['border_soft']};
                color: {colors['text_muted']};
            }}
        """

    @staticmethod
    def light_theme():
        return Themes._theme_template(
            {
                "window_bg": "#f4f5f7",
                "panel_bg": "#f8f9fb",
                "text": "#1f2328",
                "text_muted": "#6a737d",
                "border": "#aeb4bd",
                "border_soft": "#c8cdd5",
                "button_bg": "#e9edf2",
                "button_hover": "#dfe5ec",
                "button_pressed": "#d3dbe4",
                "button_text": "#1f2328",
                "input_bg": "#ffffff",
                "console_bg": "#eef2f5",
                "console_input_bg": "#ffffff",
                "console_border": "#9ea7b2",
                "console_button_bg": "#e2e7ed",
                "console_button_hover": "#d8dee6",
                "menu_bg": "#e9edf2",
                "menu_hover": "#d8e0ea",
                "accent": "#2f81f7",
            }
        )

    @staticmethod
    def dark_theme():
        return Themes._theme_template(
            {
                "window_bg": "#1f2328",
                "panel_bg": "#252b32",
                "text": "#e6edf3",
                "text_muted": "#9da7b3",
                "border": "#4f5a68",
                "border_soft": "#3f4752",
                "button_bg": "#2f3742",
                "button_hover": "#384250",
                "button_pressed": "#2a323d",
                "button_text": "#e6edf3",
                "input_bg": "#212830",
                "console_bg": "#11161c",
                "console_input_bg": "#171d24",
                "console_border": "#586474",
                "console_button_bg": "#2c3540",
                "console_button_hover": "#384250",
                "menu_bg": "#252b32",
                "menu_hover": "#3a4452",
                "accent": "#4f8cff",
            }
        )

    @staticmethod
    def green_theme():
        return Themes._theme_template(
            {
                "window_bg": "#0d0f10",
                "panel_bg": "#141819",
                "text": "#e3e8ea",
                "text_muted": "#97a4a8",
                "border": "#445256",
                "border_soft": "#252d2f",
                "button_bg": "#1b2426",
                "button_hover": "#243033",
                "button_pressed": "#161d1f",
                "button_text": "#edf3f4",
                "input_bg": "#0f1415",
                "console_bg": "#090b0c",
                "console_input_bg": "#0d1112",
                "console_border": "#48575b",
                "console_button_bg": "#1b2426",
                "console_button_hover": "#243033",
                "menu_bg": "#131819",
                "menu_hover": "#243033",
                "accent": "#4f7f69",
            }
        )

    @staticmethod
    def get_theme(name):
        if name == "system":
            from PyQt5.QtWidgets import QApplication

            app = QApplication.instance()
            if app:
                bg_color = app.palette().window().color()
                if bg_color.lightness() > 128:
                    return Themes.light_theme()
                return Themes.dark_theme()
            return Themes.light_theme()
        if name == "dark":
            return Themes.dark_theme()
        if name == "green":
            return Themes.green_theme()
        return Themes.light_theme()
