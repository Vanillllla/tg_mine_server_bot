from pathlib import Path
from typing import Any

from app.core.json_store import read_json, write_json_atomic
from app.core.settings import AppSettings, DEFAULT_PANEL
from app.models.settings import JavaRuntime, PublicPanelSettings, UpsertJavaRuntimeRequest


BUILTIN_JAVA_RUNTIMES = [
    {
        "id": "system",
        "display_name": "System java from PATH",
        "path": "java",
    },
    {
        "id": "java8_oracle",
        "display_name": "Java 8 - Oracle JRE 1.8.0_401",
        "path": r"C:\Program Files\Java\jre-1.8\bin\java.exe",
    },
    {
        "id": "java21_temurin",
        "display_name": "Java 21 - Temurin",
        "path": r"C:\Program Files\Java\java21\bin\java.exe",
    },
]


class PanelSettingsService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def public_settings(self) -> PublicPanelSettings:
        panel = self._read_panel()
        changed = self._ensure_public_link_defaults(panel)
        if changed:
            self._write_panel(panel)
        return PublicPanelSettings(links=panel["links"])

    def list_java_runtimes(self) -> list[JavaRuntime]:
        panel = self._read_panel()
        changed = self._ensure_java_defaults(panel)
        if changed:
            self._write_panel(panel)
        return self._java_runtimes_from_panel(panel)

    def upsert_java_runtime(self, payload: UpsertJavaRuntimeRequest) -> JavaRuntime:
        panel = self._read_panel()
        self._ensure_java_defaults(panel)
        java = panel.setdefault("java", {})
        runtimes = java.setdefault("runtimes", [])

        updated = {
            "id": payload.id,
            "display_name": payload.display_name,
            "path": payload.path,
        }
        for index, item in enumerate(runtimes):
            if item.get("id") == payload.id:
                runtimes[index] = updated
                break
        else:
            runtimes.append(updated)

        if payload.is_default:
            java["default_runtime_id"] = payload.id

        self._write_panel(panel)
        return next(runtime for runtime in self.list_java_runtimes() if runtime.id == payload.id)

    def set_default_java_runtime(self, runtime_id: str) -> JavaRuntime:
        panel = self._read_panel()
        self._ensure_java_defaults(panel)
        runtimes = panel.setdefault("java", {}).setdefault("runtimes", [])
        if not any(item.get("id") == runtime_id for item in runtimes):
            raise KeyError(runtime_id)
        panel["java"]["default_runtime_id"] = runtime_id
        self._write_panel(panel)
        return next(runtime for runtime in self.list_java_runtimes() if runtime.id == runtime_id)

    def _read_panel(self) -> dict[str, Any]:
        return read_json(self.settings.panel_config_path, default={})

    def _write_panel(self, panel: dict[str, Any]) -> None:
        write_json_atomic(self.settings.panel_config_path, panel)

    @staticmethod
    def _java_runtimes_from_panel(panel: dict[str, Any]) -> list[JavaRuntime]:
        java = panel.setdefault("java", {})
        default_id = str(java.get("default_runtime_id", "") or "")
        runtimes = [
            JavaRuntime(
                id=str(item["id"]),
                display_name=str(item["display_name"]),
                path=str(item["path"]),
                is_default=str(item["id"]) == default_id,
            )
            for item in java.get("runtimes", [])
        ]
        if runtimes and not any(runtime.is_default for runtime in runtimes):
            runtimes[0].is_default = True
        return runtimes

    @staticmethod
    def _ensure_java_defaults(panel: dict[str, Any]) -> bool:
        java = panel.setdefault("java", {})
        runtimes = java.setdefault("runtimes", [])
        changed = False

        known_ids = {str(item.get("id")) for item in runtimes}
        for runtime in BUILTIN_JAVA_RUNTIMES:
            if runtime["id"] == "system" or Path(runtime["path"]).is_file():
                if runtime["id"] not in known_ids:
                    runtimes.append(runtime.copy())
                    known_ids.add(runtime["id"])
                    changed = True

        if not java.get("default_runtime_id"):
            preferred = "java8_oracle" if "java8_oracle" in known_ids else runtimes[0]["id"]
            java["default_runtime_id"] = preferred
            changed = True

        return changed

    @staticmethod
    def _ensure_public_link_defaults(panel: dict[str, Any]) -> bool:
        links = panel.setdefault("links", {})
        discord = links.setdefault("discord", {})
        changed = False

        default_discord = DEFAULT_PANEL["links"]["discord"]
        for key, value in default_discord.items():
            if not discord.get(key):
                discord[key] = value
                changed = True

        return changed
