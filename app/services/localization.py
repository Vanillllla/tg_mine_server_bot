
"""Модуль для загрузки и получения текстов локализации из JSON-файлов.

Ожидаемая структура проекта:
    project/
    ├── localization.py
    └── locales/
        ├── ru.json
        ├── en.json
        └── ...

Каждый JSON-файл локализации должен содержать блок ``meta`` с описанием языка
и произвольные вложенные разделы с текстами интерфейса. Например:

    {
      "meta": {
        "code": "ru",
        "name": "Русский",
        "flag": ""
      },
      "buttons": {
        "start_server": "🚀 Запустить сервер"
      }
    }

Тексты можно получать по точечному ключу, например:
``buttons.start_server``.
"""

import json
from pathlib import Path


class Locales:
    """Класс для работы с локализациями приложения.

    Класс автоматически ищет все JSON-файлы в папке ``locales``, которая должна
    находиться рядом с этим Python-файлом, считывает метаданные языков и даёт
    методы для получения:

    - списка кнопок выбора языка;
    - соответствия текста кнопки коду языка;
    - конкретной строки перевода по ключу.

    Attributes:
        default_language: Код языка, который используется по умолчанию.
        locales_dir: Путь к папке с JSON-файлами локализаций.
        languages: Словарь с данными доступных языков.
    """

    def __init__(self, default_language: str = "ru"):
        """Инициализирует менеджер локализаций.

        Args:
            default_language: Код языка по умолчанию. Используется, если язык
                не указан при получении текста или если передан неизвестный код
                языка.
        """
        self.default_language = default_language
        self.locales_dir = Path(__file__).parent / "locales"
        self.languages = self._load_available_languages()

    def _load_available_languages(self) -> dict[str, dict]:
        """Загружает список доступных языков из папки ``locales``.

        Метод просматривает все файлы с расширением ``.json`` в папке
        ``self.locales_dir``. Из каждого файла берётся блок ``meta``:

        - ``code`` — код языка;
        - ``name`` — отображаемое название языка;
        - ``flag`` — флаг или emoji перед названием языка.

        Если в ``meta`` нет отдельных полей, используются запасные значения:
        имя файла вместо кода языка, код языка вместо названия и пустая строка
        вместо флага.

        Returns:
            Словарь доступных языков. Ключ — код языка, значение — словарь с
            данными языка: ``code``, ``name``, ``flag`` и ``file_path``.
        """
        languages = {}

        for file_path in self.locales_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            meta = data.get("meta", {})

            code = meta.get("code", file_path.stem)
            name = meta.get("name", code)
            flag = meta.get("flag", "")

            languages[code] = {
                "code": code,
                "name": name,
                "flag": flag,
                "file_path": file_path
            }

        return languages

    def get_language_button_text(self, language_code: str) -> str:
        """Возвращает текст кнопки выбора языка.

        Если для языка указан флаг, кнопка будет иметь вид ``"🇷🇺 Русский"``.
        Если флаг не указан, будет возвращено только название языка.

        Args:
            language_code: Код языка, для которого нужно получить текст кнопки.

        Returns:
            Готовый текст кнопки выбора языка.

        Raises:
            KeyError: Если ``language_code`` отсутствует в ``self.languages``.
        """
        language = self.languages[language_code]

        flag = language["flag"]
        name = language["name"]

        if flag:
            return f"{flag} {name}"

        return name

    def get_language_buttons(self) -> list[str]:
        """Возвращает список текстов кнопок выбора языка.

        Метод проходит по всем загруженным языкам и для каждого языка вызывает
        ``get_language_button_text``.

        Returns:
            Список строк, которые можно использовать как текст кнопок в меню
            выбора языка.
        """
        return [
            self.get_language_button_text(language_code)
            for language_code in self.languages
        ]

    def get_language_buttons_map(self) -> dict[str, str]:
        """Возвращает соответствие текста кнопки коду языка.

        Это удобно использовать при обработке нажатия на кнопку: пользователь
        отправляет текст кнопки, а программа по этому словарю получает код
        выбранного языка.

        Returns:
            Словарь вида ``{"Русский": "ru"}``, где ключ — текст кнопки,
            значение — код языка.
        """
        return {
            self.get_language_button_text(language_code): language_code
            for language_code in self.languages
        }

    def get_languages_data(self) -> tuple[list[str], dict[str, str]]:
        """Возвращает данные для построения меню выбора языка.

        Метод объединяет два часто используемых результата:
        список текстов кнопок и словарь соответствия кнопок кодам языков.

        Returns:
            Кортеж из двух элементов:
            - список текстов кнопок выбора языка;
            - словарь соответствия текста кнопки коду языка.
        """
        return self.get_language_buttons(), self.get_language_buttons_map()


    def get_button_key_by_text(
        self,
        button_text: str,
        language_code: str | None = None
    ) -> str | None:
        """Возвращает ключ кнопки по её тексту.

        Метод нужен для обработки сообщений от пользователя, когда Telegram
        присылает не саму кнопку, а её текст. Например, если пользователь
        нажал кнопку ``"🚀 Запустить сервер"``, метод вернёт ключ
        ``"start_server"``.

        Поиск выполняется только внутри раздела ``buttons`` выбранного
        JSON-файла локализации. Для ускорения результат один раз сохраняется
        во внутренний кэш ``self._button_keys_cache`` и повторно используется
        при следующих проверках.

        Args:
            button_text: Текст, который нужно проверить. Обычно это
                ``message.text`` из Telegram-бота.
            language_code: Код языка, в котором нужно искать кнопку. Если
                ``None``, используется язык по умолчанию. Если передан
                неизвестный код языка, используется язык по умолчанию.

        Returns:
            Ключ кнопки из раздела ``buttons``, если текст найден.
            Если такого текста кнопки нет, возвращается ``None``.

        Raises:
            FileNotFoundError: Если файл выбранной локализации был удалён после
                загрузки списка языков.
            json.JSONDecodeError: Если JSON-файл локализации повреждён или имеет
                некорректный синтаксис.
        """
        language_code = language_code or self.default_language

        if language_code not in self.languages:
            language_code = self.default_language

        if not hasattr(self, "_button_keys_cache"):
            self._button_keys_cache = {}

        if language_code not in self._button_keys_cache:
            file_path = self.languages[language_code]["file_path"]

            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            buttons = data.get("buttons", {})

            self._button_keys_cache[language_code] = {
                str(button_text): button_key
                for button_key, button_text in buttons.items()
            }

        return self._button_keys_cache[language_code].get(button_text)

    def get_text(
        self,
        key: str,
        language_code: str | None = None,
        default: str | None = None
    ) -> str:
        """Возвращает текст локализации по точечному ключу.

        Ключ должен указывать путь к значению внутри JSON-файла через точки.
        Например, ключ ``"buttons.start_server"`` будет искать значение:

        ``data["buttons"]["start_server"]``

        Если язык не передан, используется ``self.default_language``. Если
        передан неизвестный код языка, также используется язык по умолчанию.

        Args:
            key: Точечный ключ нужного текста, например
                ``"messages.choose_language"``.
            language_code: Код языка, из которого нужно взять текст. Если
                ``None``, используется язык по умолчанию.
            default: Запасной текст, который будет возвращён, если ключ не
                найден в JSON-файле.

        Returns:
            Найденный текст локализации. Если ключ не найден и ``default`` не
            передан, возвращается строка вида ``"<buttons.start_server>"``.

        Raises:
            FileNotFoundError: Если файл выбранной локализации был удалён после
                загрузки списка языков.
            json.JSONDecodeError: Если JSON-файл локализации повреждён или имеет
                некорректный синтаксис.
        """
        language_code = language_code or self.default_language

        if language_code not in self.languages:
            language_code = self.default_language

        file_path = self.languages[language_code]["file_path"]

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        value = data

        try:
            for part in key.split("."):
                value = value[part]

            return str(value)

        except KeyError:
            if default is not None:
                return default

            return f"<{key}>"
