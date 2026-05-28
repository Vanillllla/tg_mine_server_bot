import json
import os
import shutil
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

from app.core.json_store import read_json, write_json_atomic
from app.core.settings import AppSettings
from app.models.mod_catalog import ModCatalogItem, ModCatalogItemRequest
from app.models.server import ServerInstance
from app.services.map_integration import NETWORK_TIMEOUT_SECONDS


MODRINTH_PROJECT_VERSION_URL = "https://api.modrinth.com/v2/project/{project}/version"
MOD_LOADERS = {"fabric", "forge", "neoforge"}
SERVER_TYPE_TO_LOADER = {
    "paper": "spigot",
    "purpur": "spigot",
    "spigot": "spigot",
    "bukkit": "spigot",
    "folia": "folia",
    "sponge": "sponge",
    "fabric": "fabric",
    "forge": "forge",
    "neoforge": "neoforge",
}


class ModCatalogService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def list_items(self) -> list[ModCatalogItem]:
        return [
            self._item_from_payload(item_id, payload)
            for item_id, payload in self._read_catalog().items()
        ]

    def add_remote_item(self, payload: ModCatalogItemRequest) -> ModCatalogItem:
        if payload.source_type == "local":
            raise ValueError("local_mod_requires_upload")
        if not payload.source:
            raise ValueError("mod_source_required")

        catalog = self._read_catalog()
        now = datetime.now(timezone.utc)
        current = catalog.get(payload.id, {})
        item = ModCatalogItem(
            **{
                **current,
                **payload.model_dump(),
                "updated_at": now,
                "created_at": current.get("created_at") or now,
                "last_error": "",
            }
        )
        catalog[item.id] = self._item_payload(item)
        self._write_catalog(catalog)
        return item

    def add_uploaded_item(
        self,
        payload: ModCatalogItemRequest,
        file_name: str,
        source: BinaryIO,
    ) -> ModCatalogItem:
        if not file_name.lower().endswith(".jar") or Path(file_name).name != file_name:
            raise ValueError("mod_file_must_be_jar")

        cache_path = self._cache_path(payload.id, file_name)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._copy_stream_atomic(source, cache_path)

        catalog = self._read_catalog()
        now = datetime.now(timezone.utc)
        current = catalog.get(payload.id, {})
        item = ModCatalogItem(
            **{
                **current,
                **payload.model_dump(),
                "source_type": "local",
                "source": payload.source,
                "file_name": file_name,
                "cached_path": self._relative_cache_path(cache_path),
                "updated_at": now,
                "created_at": current.get("created_at") or now,
                "last_error": "",
            }
        )
        catalog[item.id] = self._item_payload(item)
        self._write_catalog(catalog)
        return item

    def delete_item(self, item_id: str, delete_cached_file: bool = False) -> None:
        catalog = self._read_catalog()
        if item_id not in catalog:
            raise KeyError(item_id)
        item = self._item_from_payload(item_id, catalog[item_id])
        del catalog[item_id]
        self._write_catalog(catalog)
        if delete_cached_file and item.cached_path:
            self._absolute_cache_path(item.cached_path).unlink(missing_ok=True)

    def auto_install_for_server(self, server: ServerInstance) -> list[ModCatalogItem]:
        installed: list[ModCatalogItem] = []
        for item in self.list_items():
            if not item.enabled or not self._matches_server(item, server):
                continue
            try:
                source_path, resolved = self._ensure_cached(item, server)
                self._copy_to_server(source_path, server)
                installed.append(resolved.model_copy(update={"last_error": ""}))
            except Exception as exc:
                self._mark_error(item.id, str(exc))
        return installed

    def _ensure_cached(self, item: ModCatalogItem, server: ServerInstance) -> tuple[Path, ModCatalogItem]:
        if item.cached_path:
            cached = self._absolute_cache_path(item.cached_path)
            if cached.is_file():
                return cached, item

        if item.source_type == "local":
            raise FileNotFoundError("cached_mod_file_not_found")

        if item.source_type == "modrinth":
            version = self._resolve_modrinth_version(item, server)
            file_name = version["file_name"]
            download_url = version["download_url"]
            version_number = version["version"]
        else:
            file_name = Path(urllib.parse.urlparse(item.source).path).name or f"{item.id}.jar"
            download_url = item.source
            version_number = item.version

        if not file_name.lower().endswith(".jar"):
            raise ValueError("resolved_mod_file_must_be_jar")
        target = self._cache_path(item.id, file_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._download_file(download_url, target)

        updated = item.model_copy(
            update={
                "file_name": file_name,
                "cached_path": self._relative_cache_path(target),
                "version": version_number,
                "last_error": "",
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._store_item(updated)
        return target, updated

    def _resolve_modrinth_version(self, item: ModCatalogItem, server: ServerInstance) -> dict[str, str]:
        loader = self._server_loader(server.server_type)
        params = {"loaders": json.dumps([loader]), "include_changelog": "false"}
        if server.minecraft_version:
            params["game_versions"] = json.dumps([server.minecraft_version])
        url = f"{MODRINTH_PROJECT_VERSION_URL.format(project=urllib.parse.quote(item.source))}?{urllib.parse.urlencode(params)}"
        versions = self._request_json(url)
        if not isinstance(versions, list):
            versions = []
        selected = self._select_modrinth_file(versions)
        if selected is None:
            raise ValueError("compatible_mod_version_not_found")
        return selected

    @staticmethod
    def _select_modrinth_file(versions: list[dict[str, Any]]) -> dict[str, str] | None:
        for version in sorted(versions, key=lambda item: str(item.get("date_published", "")), reverse=True):
            files = version.get("files", [])
            if not isinstance(files, list):
                continue
            file_payload = next(
                (
                    file
                    for file in files
                    if file.get("primary") and str(file.get("filename", "")).lower().endswith(".jar")
                ),
                None,
            ) or next(
                (
                    file
                    for file in files
                    if str(file.get("filename", "")).lower().endswith(".jar")
                ),
                None,
            )
            if file_payload and file_payload.get("url"):
                return {
                    "file_name": str(file_payload.get("filename", "mod.jar")),
                    "download_url": str(file_payload["url"]),
                    "version": str(version.get("version_number", "")),
                }
        return None

    def _copy_to_server(self, source_path: Path, server: ServerInstance) -> None:
        loader = self._server_loader(server.server_type)
        directory = "mods" if loader in MOD_LOADERS else "plugins"
        target = Path(server.server_dir) / directory / source_path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)

    @classmethod
    def _matches_server(cls, item: ModCatalogItem, server: ServerInstance) -> bool:
        server_type = str(server.server_type or "").lower()
        if item.server_types and server_type not in {value.lower() for value in item.server_types}:
            return False
        if item.minecraft_versions and server.minecraft_version not in item.minecraft_versions:
            return False
        try:
            cls._server_loader(server_type)
        except ValueError:
            return False
        return True

    @staticmethod
    def _server_loader(server_type: str) -> str:
        loader = SERVER_TYPE_TO_LOADER.get(str(server_type or "").strip().lower())
        if not loader:
            raise ValueError("server_type_not_supported_for_mods")
        return loader

    def _read_catalog(self) -> dict[str, dict[str, Any]]:
        return read_json(self.settings.mod_catalog_path, default={})

    def _write_catalog(self, catalog: dict[str, dict[str, Any]]) -> None:
        write_json_atomic(self.settings.mod_catalog_path, catalog)

    def _store_item(self, item: ModCatalogItem) -> None:
        catalog = self._read_catalog()
        catalog[item.id] = self._item_payload(item)
        self._write_catalog(catalog)

    def _mark_error(self, item_id: str, message: str) -> None:
        catalog = self._read_catalog()
        if item_id not in catalog:
            return
        catalog[item_id]["last_error"] = message
        catalog[item_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_catalog(catalog)

    @staticmethod
    def _item_payload(item: ModCatalogItem) -> dict[str, Any]:
        payload = item.model_dump(mode="json")
        payload.pop("id", None)
        return payload

    @staticmethod
    def _item_from_payload(item_id: str, payload: dict[str, Any]) -> ModCatalogItem:
        return ModCatalogItem(id=item_id, **payload)

    def _cache_path(self, item_id: str, file_name: str) -> Path:
        return (self.settings.mod_cache_dir / item_id / Path(file_name).name).resolve()

    def _relative_cache_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.settings.mod_cache_dir.resolve()).as_posix()

    def _absolute_cache_path(self, relative_path: str) -> Path:
        target = (self.settings.mod_cache_dir / relative_path).resolve()
        target.relative_to(self.settings.mod_cache_dir.resolve())
        return target

    @staticmethod
    def _copy_stream_atomic(source: BinaryIO, target: Path) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            with tmp_path.open("wb") as output:
                shutil.copyfileobj(source, output)
            os.replace(tmp_path, target)
        finally:
            tmp_path.unlink(missing_ok=True)

    @staticmethod
    def _request_json(url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": "MinecraftWebPanel/0.1"})
        with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _download_file(url: str, target: Path) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MinecraftWebPanel/0.1"})
            with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
                with tmp_path.open("wb") as output:
                    shutil.copyfileobj(response, output)
            os.replace(tmp_path, target)
        finally:
            tmp_path.unlink(missing_ok=True)
