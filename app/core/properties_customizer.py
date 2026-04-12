import json
from pathlib import Path
from typing import Dict, Any

from app.core.paths import config_path


class PropertiesCustomizer:
    """Utility to read and update server.properties for selected core."""

    @staticmethod
    def _get_core_folder(core_id: str) -> Path:
        with config_path("cores.json").open("r", encoding="utf-8") as file:
            cores = json.load(file)
        if core_id not in cores:
            raise ValueError("core_not_found_in_cores_json")
        folder = cores[core_id].get("core_folder", "")
        if not folder:
            raise ValueError("core_folder_not_set")
        path = Path(folder)
        if not path.exists():
            raise FileNotFoundError(f"core_folder_missing: {path}")
        return path

    @classmethod
    def _properties_path(cls, core_id: str) -> Path:
        folder = cls._get_core_folder(core_id)
        return folder / "server.properties"

    @staticmethod
    def _parse_properties(text: str) -> Dict[str, str]:
        props: Dict[str, str] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            props[key.strip()] = value.strip()
        return props

    @classmethod
    def get_properties(cls, core: str) -> Dict[str, str]:
        """Return dict of server.properties values for given core id."""
        path = cls._properties_path(str(core))
        if not path.is_file():
            raise FileNotFoundError(f"server_properties_not_found: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        return cls._parse_properties(text)

    @classmethod
    def set_properties(cls, core: str, changes: Dict[str, Any]) -> None:
        """
        Apply provided key/value pairs into server.properties of given core.
        Preserves other lines and comments where possible.
        """
        core_id = str(core)
        path = cls._properties_path(core_id)
        if not path.is_file():
            raise FileNotFoundError(f"server_properties_not_found: {path}")

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

        def upsert(key: str, value: str):
            prefix = f"{key}="
            for idx, line in enumerate(lines):
                if line.startswith(prefix):
                    lines[idx] = f"{key}={value}"
                    return
            lines.append(f"{key}={value}")

        for k, v in changes.items():
            upsert(str(k), str(v))

        final_text = "\n".join(lines)
        if not final_text.endswith("\n"):
            final_text += "\n"
        path.write_text(final_text, encoding="utf-8")


__all__ = ["PropertiesCustomizer"]
