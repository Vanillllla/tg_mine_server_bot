import json
from pathlib import Path
from typing import Dict, Any

from app.core.paths import config_path


class PropertiesCustomizer:
    """
    Helper for reading and updating server.properties of a selected core.
    """

    @staticmethod
    def _load_core_info(core_id: str) -> Dict[str, Any]:
        cores_path = config_path("cores.json")
        with cores_path.open("r", encoding="utf-8") as file:
            cores = json.load(file)

        if not core_id:
            raise ValueError("active_core_not_selected")
        if core_id not in cores:
            raise ValueError("active_core_not_found_in_cores")

        return cores[core_id]

    @classmethod
    def _properties_path(cls, core_id: str) -> Path:
        core_info = cls._load_core_info(core_id)
        core_folder = core_info.get("core_folder")
        if not core_folder:
            raise ValueError("active_core_folder_not_set")

        properties_path = Path(core_folder) / "server.properties"
        if not properties_path.is_file():
            raise FileNotFoundError(f"server_properties_not_found: {properties_path}")
        return properties_path

    @classmethod
    def get_properties(cls, core: str) -> Dict[str, str]:
        """
        Return dict with all key/value pairs from server.properties
        of selected core.
        """
        path = cls._properties_path(str(core))
        props: Dict[str, str] = {}

        with path.open("r", encoding="utf-8", errors="replace") as file:
            for line in file:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()

        return props

    @classmethod
    def set_properties(cls, core: str, values: Dict[str, Any]) -> None:
        """
        Update provided keys in server.properties for selected core.
        Unspecified keys stay untouched. Adds missing keys to the end.
        """
        if not values:
            return

        path = cls._properties_path(str(core))
        original_text = path.read_text(encoding="utf-8", errors="replace")
        lines = original_text.splitlines()

        def upsert(key: str, value: Any):
            value_str = str(value)
            prefix = f"{key}="
            for idx, line in enumerate(lines):
                if line.strip().startswith(prefix):
                    lines[idx] = f"{key}={value_str}"
                    return
            lines.append(f"{key}={value_str}")

        for key, value in values.items():
            upsert(key, value)

        final_text = "\n".join(lines)
        if original_text.endswith("\n"):
            final_text += "\n"

        path.write_text(final_text, encoding="utf-8")

    @classmethod
    def get_properties_path(cls, core: str) -> Path:
        """
        Return Path to server.properties for selected core.
        """
        return cls._properties_path(str(core))
