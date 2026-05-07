
class BotKeyboards:
    @staticmethod
    def get_keyboard(status: int = 0, server_status: bool = False,
                     menu: str = "main_menu") -> ReplyKeyboardMarkup:
        if status == 0:
            if menu == "main_menu":
                return BotKeyboards.user_main(server_status)
            elif menu == "settings":
                return BotKeyboards.user_settings()
        if status == 1:
            if menu in {"main", "main_menu"}:
                return BotKeyboards.admin_main(server_status)
            elif menu == "settings":
                return BotKeyboards.admin_settings()
            elif menu == "console":
                return BotKeyboards.admin_console()

    @staticmethod
    def user_main(server_status: bool = False) -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text=("🚀 Запустить сервер" if not server_status else "👥 Онлайн на сервере"))],
            [KeyboardButton(text="⚙️ Мои настройки"), KeyboardButton(text="test")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def user_settings() -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def admin_main(server_status: bool = False) -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text="🟢 Запустить сервер 🟢") if not server_status else KeyboardButton(
                text="🔴 Остановить сервер 🔴")],
            [KeyboardButton(text="👥 Онлайн на сервере"), KeyboardButton(text="📟 Консоль")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="🔄 Перезапустить бота")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def admin_console() -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text="⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def admin_settings(notifications_enabled: bool = True) -> ReplyKeyboardMarkup:
        notify_button = (
            "🟢 Выключить уведомления о запуске"
            if notifications_enabled
            else "🔴 Включить уведомления о запуске"
        )

        keyboard = [
            [KeyboardButton(text="🧩 Server properties"), KeyboardButton(text="📊 Нагрузка сервера")],
            # [KeyboardButton(text="👤 Пользователи бота")],
            # [KeyboardButton(text=notify_button)],
            [KeyboardButton(text="⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )

    @staticmethod
    def admin_users() -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton(text="📋 Список пользователей")],
            [KeyboardButton(text="➕ Добавить пользователя"), KeyboardButton(text="➖ Удалить пользователя")],
            [KeyboardButton(text="🔒 Права доступа")],
            [KeyboardButton(text="⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )
