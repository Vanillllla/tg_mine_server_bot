class Themes:
    @staticmethod
    def _theme_template(colors):
        return f"""
            QMainWindow, QDialog {{
                background-color: {colors['window_bg']};
                color: {colors['text']};
                font-size: 10pt;
            }}
            QWidget#centralwidget {{
                background-color: {colors['window_bg']};
            }}
            QMenuBar, QStatusBar {{
                background-color: {colors['menu_bg']};
            }}
            QFrame#frame_2 {{
                background-color: {colors['panel_bg']};
                border: 1px solid {colors['border']};
                border-radius: 14px;
            }}
            QGroupBox {{
                border: 1px solid {colors['border']};
                background-color: {colors['panel_bg']};
                border-radius: 14px;
                margin-top: 14px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: {colors['title_text']};
                background-color: {colors['window_bg']};
                border: none;
                font-weight: 600;
            }}
            QPushButton {{
                background-color: {colors['button_bg']};
                border: 1px solid {colors['border']};
                color: {colors['button_text']};
                border-radius: 10px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {colors['button_hover']};
                border-color: {colors['button_border_hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['button_pressed']};
            }}
            QPushButton:disabled {{
                color: {colors['text_muted']};
                border-color: {colors['border_soft']};
            }}
            QPushButton#startServerButton, QPushButton#bot_control_button, QPushButton#saveOut, QPushButton#selectFileButton {{
                background-color: {colors['button_primary_bg']};
                border: 1px solid {colors['button_primary_border']};
                color: {colors['button_primary_text']};
                font-weight: 600;
            }}
            QPushButton#startServerButton:hover, QPushButton#bot_control_button:hover, QPushButton#saveOut:hover, QPushButton#selectFileButton:hover {{
                background-color: {colors['button_primary_hover']};
                border-color: {colors['button_primary_border_hover']};
            }}
            QPushButton#startServerButton:pressed, QPushButton#bot_control_button:pressed, QPushButton#saveOut:pressed, QPushButton#selectFileButton:pressed {{
                background-color: {colors['button_primary_pressed']};
            }}
            QLineEdit, QPlainTextEdit, QTextEdit {{
                background-color: {colors['input_bg']};
                border: 1px solid {colors['border']};
                color: {colors['text']};
                selection-background-color: {colors['accent']};
                border-radius: 10px;
                padding: 6px 8px;
            }}
            QPlainTextEdit#console_output {{
                background-color: {colors['console_bg']};
                border: 1px solid {colors['console_border']};
                color: {colors['text']};
                border-radius: 12px;
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
            QFrame#line_3 {{
                background-color: transparent;
                border: none;
                border-top: 1px solid #245748;
            }}
            QPushButton#console_send_button:hover {{
                background-color: {colors['console_button_hover']};
                border-color: {colors['button_border_hover']};
            }}
            QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
                border: 1px solid {colors['accent']};
            }}
            QComboBox {{
                border: 1px solid {colors['border']};
                background-color: {colors['input_bg']};
                color: {colors['text']};
                border-radius: 10px;
                padding: 5px 10px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {colors['input_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                selection-background-color: {colors['accent']};
            }}
            QComboBox:on {{
                border-color: {colors['accent']};
            }}
            QCheckBox {{
                background-color: transparent;
                spacing: 6px;
                color: {colors['text']};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {colors['border']};
                background-color: {colors['input_bg']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['accent']};
                border-color: {colors['accent']};
            }}
            QLabel {{
                background-color: transparent;
                border: none;
                color: {colors['text']};
            }}
            QLabel#botStatusLabel {{
                color: {colors['title_text']};
            }}
            QLabel#botStatusLabel_ind {{
                border: 1px solid {colors['border']};
                border-radius: 14px;
                background-color: transparent;
                font-weight: 700;
                padding: 0 12px;
            }}
            QLabel#coreLabel, QLabel#versionLabel, QLabel#versionLabel_2, QLabel#versionLabel_3 {{
                color: {colors['value_text']};
                font-weight: 600;
            }}
            QProgressBar {{
                border: 1px solid {colors['border']};
                text-align: center;
                background-color: {colors['input_bg']};
                color: {colors['text']};
                border-radius: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {colors['accent']};
                border-radius: 7px;
            }}
            QMenuBar {{
                background-color: {colors['menu_bg']};
                color: {colors['text']};
                border-bottom: 1px solid {colors['border_soft']};
            }}
            QMenuBar::item {{
                padding: 5px 10px;
                border-radius: 6px;
                margin: 2px 4px;
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
            QScrollBar:vertical {{
                background: {colors['scrollbar_bg']};
                width: 12px;
                margin: 4px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {colors['scrollbar_handle']};
                min-height: 28px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {colors['scrollbar_handle_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {colors['scrollbar_bg']};
                height: 12px;
                margin: 4px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: {colors['scrollbar_handle']};
                min-width: 28px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {colors['scrollbar_handle_hover']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QToolTip {{
                background-color: {colors['panel_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                padding: 4px 6px;
            }}
            QFrame[frameShape="4"], Line {{
                color: {colors['line']};
                background-color: {colors['line']};
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
                "title_text": "#1f2328",
                "title_bg": "transparent",
                "title_border": "transparent",
                "value_text": "#0969da",
                "border": "#aeb4bd",
                "border_soft": "#c8cdd5",
                "line": "#cfd6df",
                "button_bg": "#e9edf2",
                "button_hover": "#dfe5ec",
                "button_pressed": "#d3dbe4",
                "button_border_hover": "#8c959f",
                "button_text": "#1f2328",
                "button_primary_bg": "#2f81f7",
                "button_primary_hover": "#1f6feb",
                "button_primary_pressed": "#1158c7",
                "button_primary_border": "#1b6bd1",
                "button_primary_border_hover": "#0f5ec2",
                "button_primary_text": "#ffffff",
                "input_bg": "#ffffff",
                "console_bg": "#eef2f5",
                "console_input_bg": "#ffffff",
                "console_border": "#9ea7b2",
                "console_button_bg": "#e2e7ed",
                "console_button_hover": "#d8dee6",
                "menu_bg": "#e9edf2",
                "menu_hover": "#d8e0ea",
                "scrollbar_bg": "#edf1f5",
                "scrollbar_handle": "#c0c7d1",
                "scrollbar_handle_hover": "#aeb7c2",
                "accent": "#2f81f7",
            }
        )

    @staticmethod
    def dark_theme():
        return Themes._theme_template(
            {
                "window_bg": "#1f2328",
                "panel_bg": "#252b32",
                "text": "#ffffff",
                "text_muted": "#9da7b3",
                "title_text": "#f0f6fc",
                "title_bg": "transparent",
                "title_border": "transparent",
                "value_text": "#79c0ff",
                "border": "#4f5a68",
                "border_soft": "#3f4752",
                "line": "#36404a",
                "button_bg": "#2f3742",
                "button_hover": "#384250",
                "button_pressed": "#2a323d",
                "button_border_hover": "#6b7788",
                "button_text": "#e6edf3",
                "button_primary_bg": "#2f6feb",
                "button_primary_hover": "#3b82ff",
                "button_primary_pressed": "#255bc0",
                "button_primary_border": "#4f8cff",
                "button_primary_border_hover": "#77a2ff",
                "button_primary_text": "#f8fbff",
                "input_bg": "#212830",
                "console_bg": "#11161c",
                "console_input_bg": "#171d24",
                "console_border": "#586474",
                "console_button_bg": "#2c3540",
                "console_button_hover": "#384250",
                "menu_bg": "#252b32",
                "menu_hover": "#3a4452",
                "scrollbar_bg": "#20262d",
                "scrollbar_handle": "#4b5664",
                "scrollbar_handle_hover": "#647181",
                "accent": "#4f8cff",
            }
        )

    @staticmethod
    def green_theme():
        return Themes._theme_template(
            {
                "window_bg": "#071311",
                "panel_bg": "#0c1c18",
                "text": "#dff7ee",
                "text_muted": "#87b7a8",
                "title_text": "#b9f5dd",
                "title_bg": "transparent",
                "title_border": "transparent",
                "value_text": "#7cf0b8",
                "border": "#245748",
                "border_soft": "#16352d",
                "line": "#1a4137",
                "button_bg": "#112923",
                "button_hover": "#17372f",
                "button_pressed": "#0d211c",
                "button_border_hover": "#2f6d59",
                "button_text": "#dff7ee",
                "button_primary_bg": "#274f3e",
                "button_primary_hover": "#32684f",
                "button_primary_pressed": "#1c3d2f",
                "button_primary_border": "#8dff77",
                "button_primary_border_hover": "#b7ffaa",
                "button_primary_text": "#f4fff0",
                "input_bg": "#0a1714",
                "console_bg": "#050d0b",
                "console_input_bg": "#081310",
                "console_border": "#2f6d59",
                "console_button_bg": "#15342c",
                "console_button_hover": "#1d473c",
                "menu_bg": "#0a1714",
                "menu_hover": "#183b31",
                "scrollbar_bg": "#081411",
                "scrollbar_handle": "#215343",
                "scrollbar_handle_hover": "#2d705a",
                "accent": "#8dff77",
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
