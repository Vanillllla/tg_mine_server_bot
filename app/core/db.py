import sqlite3
from typing import Any

from app.core.paths import CONFIG_DIR, USERS_DB_PATH


class UsersDB:
    TABLE_NAME = "Users"
    COLUMN_NAMES = ["id", "status", "tg_id", "tg_nickname", "game_nickname"]
    COLUMN_TYPES = {
        "id": int,
        "status": int,
        "tg_id": int,
        "tg_nickname": str,
        "game_nickname": str,
    }

    def init(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status INTEGER DEFAULT 1,
                    tg_id INTEGER UNIQUE,
                    tg_nickname TEXT DEFAULT '',
                    game_nickname TEXT DEFAULT ''
                )
                """
            )
            conn.commit()

    @staticmethod
    def _connect() -> sqlite3.Connection:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _default_value(self, column_name: str) -> Any:
        column_type = self.COLUMN_TYPES.get(column_name, str)
        if column_type is int:
            return 0
        return ""

    @staticmethod
    def _empty_result_for_name(name: str) -> Any:
        if name == "dict":
            return {}
        if name == "list":
            return []
        return 0

    def _error(self, result_type: str, message: str) -> Any:
        print(f"DB error: {message}")
        return self._empty_result_for_name(result_type)

    def _check_column(self, column_name: str) -> bool:
        return str(column_name) in self.COLUMN_NAMES

    def _normalize_input_value(self, column_name: str, value: Any, *, use_default: bool = False) -> Any:
        if not self._check_column(column_name):
            raise ValueError(f"unknown_column: {column_name}")

        if value in ("", None):
            if use_default and column_name == "status":
                return 1
            if self.COLUMN_TYPES[column_name] is str:
                return ""
            return None

        try:
            if self.COLUMN_TYPES[column_name] is int:
                return int(value)
            return str(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid_value_for_{column_name}: {value}") from exc

    def _normalize_output_value(self, column_name: str, value: Any) -> Any:
        if value is None:
            return self._default_value(column_name)

        if self.COLUMN_TYPES.get(column_name) is int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
        return str(value)

    def _build_where(self, column_name: str, value: Any) -> tuple[str, tuple[Any, ...]]:
        if value is None:
            return f"{column_name} IS NULL", ()
        return f"{column_name} = ?", (value,)

    def get(self, get_column: str, search_column: str, search_value: Any) -> Any:
        try:
            self.init()
            if not self._check_column(get_column):
                return self._error("int", f"wrong_get_column: {get_column}")
            if not self._check_column(search_column):
                print(f"DB error: wrong_search_column: {search_column}")
                return self._default_value(get_column)

            normalized_value = self._normalize_input_value(search_column, search_value)
            where_query, where_params = self._build_where(search_column, normalized_value)

            with self._connect() as conn:
                row = conn.execute(
                    f"SELECT {get_column} FROM {self.TABLE_NAME} WHERE {where_query} LIMIT 1",
                    where_params,
                ).fetchone()

            if row is None:
                print(f"DB error: data_not_found: {search_column}={search_value}")
                return self._default_value(get_column)

            return self._normalize_output_value(get_column, row[get_column])
        except Exception as exc:
            print(f"DB error: {exc}")
            return self._default_value(get_column)

    def getlist(self, search_column: str, search_value: Any) -> dict[str, Any]:
        try:
            self.init()
            if not self._check_column(search_column):
                return self._error("dict", f"wrong_search_column: {search_column}")

            normalized_value = self._normalize_input_value(search_column, search_value)
            where_query, where_params = self._build_where(search_column, normalized_value)

            with self._connect() as conn:
                row = conn.execute(
                    f"SELECT * FROM {self.TABLE_NAME} WHERE {where_query} LIMIT 1",
                    where_params,
                ).fetchone()

            if row is None:
                return self._error("dict", f"data_not_found: {search_column}={search_value}")

            return {
                column_name: self._normalize_output_value(column_name, row[column_name])
                for column_name in self.COLUMN_NAMES
            }
        except Exception as exc:
            return self._error("dict", str(exc))

    def getall(self) -> list[list[Any]]:
        try:
            self.init()
            with self._connect() as conn:
                rows = conn.execute(f"SELECT * FROM {self.TABLE_NAME} ORDER BY id").fetchall()

            return [
                [self._normalize_output_value(column_name, row[column_name]) for column_name in self.COLUMN_NAMES]
                for row in rows
            ]
        except Exception as exc:
            return self._error("list", str(exc))

    def getnames(self) -> None:
        self.init()
        for index, column_name in enumerate(self.COLUMN_NAMES):
            print(f"{index} - {column_name}")

    def _parse_set_args(self, args: tuple[Any, ...]) -> tuple[list[str], list[Any]]:
        if not args:
            raise ValueError("set_arguments_is_empty")

        if len(args) == 2:
            if not self._check_column(str(args[0])):
                raise ValueError(f"wrong_column_name: {args[0]}")
            return [str(args[0])], [args[1]]

        if len(args) % 2 == 0:
            half = len(args) // 2
            first_half = [str(item) for item in args[:half]]
            if all(self._check_column(item) for item in first_half):
                return first_half, list(args[half:])

        columns = []
        for item in args:
            item_str = str(item)
            if self._check_column(item_str):
                columns.append(item_str)
                continue
            break

        if columns:
            values = list(args[len(columns):])
            if len(values) <= len(columns):
                return columns, values

        if len(args) % 2 != 0:
            raise ValueError("set_arguments_count_is_invalid")

        columns = []
        values = []
        for index in range(0, len(args), 2):
            column_name = str(args[index])
            if not self._check_column(column_name):
                raise ValueError(f"wrong_column_name: {column_name}")
            columns.append(column_name)
            values.append(args[index + 1])
        return columns, values

    def set(self, *args: Any) -> int:
        try:
            self.init()
            columns, values = self._parse_set_args(args)

            insert_columns = []
            insert_values = []
            for index, column_name in enumerate(columns):
                raw_value = values[index] if index < len(values) else None
                normalized_value = self._normalize_input_value(
                    column_name,
                    raw_value,
                    use_default=True,
                )

                insert_columns.append(column_name)
                insert_values.append(normalized_value)

            if not insert_columns:
                return self._error("int", "no_columns_for_insert")

            placeholders = ", ".join("?" for _ in insert_columns)
            columns_sql = ", ".join(insert_columns)

            with self._connect() as conn:
                cursor = conn.execute(
                    f"INSERT INTO {self.TABLE_NAME} ({columns_sql}) VALUES ({placeholders})",
                    insert_values,
                )
                conn.commit()
                return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            return self._error("int", f"integrity_error: {exc}")
        except Exception as exc:
            return self._error("int", str(exc))

    def change(self, search_column: str, search_value: Any, change_column: str, change_value: Any) -> int:
        try:
            self.init()
            if not self._check_column(search_column):
                return self._error("int", f"wrong_search_column: {search_column}")
            if not self._check_column(change_column):
                return self._error("int", f"wrong_change_column: {change_column}")

            normalized_search_value = self._normalize_input_value(search_column, search_value)
            normalized_change_value = self._normalize_input_value(change_column, change_value, use_default=True)
            where_query, where_params = self._build_where(search_column, normalized_search_value)

            with self._connect() as conn:
                cursor = conn.execute(
                    f"UPDATE {self.TABLE_NAME} SET {change_column} = ? WHERE {where_query}",
                    (normalized_change_value, *where_params),
                )
                conn.commit()

            if cursor.rowcount == 0:
                return self._error("int", f"data_not_found: {search_column}={search_value}")

            return int(cursor.rowcount)
        except sqlite3.IntegrityError as exc:
            return self._error("int", f"integrity_error: {exc}")
        except Exception as exc:
            return self._error("int", str(exc))


db = UsersDB()
