import json
import mimetypes
import os
import shutil
import socket
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.models.map import MapProvider, MapProviderVersion, MapStatusResponse, MinecraftVersion
from app.models.server import ServerInstance, ServerMapSettings
from app.services.server_instances import ServerInstanceService


MINECRAFT_VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
MODRINTH_BLUEMAP_VERSIONS_URL = "https://api.modrinth.com/v2/project/bluemap/version"
BLUEMAP_PROVIDER_ID = "bluemap"
BLUEMAP_PORT_RANGE = range(8100, 8200)
NETWORK_TIMEOUT_SECONDS = 20

PLUGIN_LOADERS = {"paper", "purpur", "spigot", "bukkit", "sponge"}
MOD_LOADERS = {"fabric", "forge", "neoforge"}
SERVER_TYPE_TO_MODRINTH_LOADER = {
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


class BlueMapIntegrationService:
    def __init__(self, instance_service: ServerInstanceService) -> None:
        self.instance_service = instance_service

    def providers(self) -> list[MapProvider]:
        return [
            MapProvider(
                id=BLUEMAP_PROVIDER_ID,
                display_name="BlueMap",
                description="3D web map rendered by a server-side Minecraft plugin or mod.",
                supported_server_types=sorted(SERVER_TYPE_TO_MODRINTH_LOADER),
            )
        ]

    def list_minecraft_versions(self) -> list[MinecraftVersion]:
        payload = self._request_json(MINECRAFT_VERSION_MANIFEST_URL)
        versions = payload.get("versions", []) if isinstance(payload, dict) else []
        return [
            MinecraftVersion(
                id=str(item.get("id", "")),
                type=str(item.get("type", "release")),
                release_time=str(item.get("releaseTime", "")),
            )
            for item in versions
            if item.get("id") and item.get("type") == "release"
        ]

    def status(self, server: ServerInstance) -> MapStatusResponse:
        map_settings = self._normalized_map_settings(server)
        jar_exists = self._jar_exists(server, map_settings)
        installed = map_settings.installed and jar_exists

        if not map_settings.enabled:
            status = "not_configured"
            message = "map_not_configured"
        elif not installed:
            status = "not_installed"
            message = "bluemap_not_installed"
        elif self._webserver_responds(map_settings):
            status = "running"
            message = "bluemap_running"
        elif map_settings.needs_restart:
            status = "needs_restart"
            message = "server_restart_required_for_bluemap"
        else:
            status = "offline"
            message = "bluemap_webserver_offline"

        return MapStatusResponse(
            configured=map_settings.enabled,
            installed=installed,
            status=status,
            provider=map_settings.provider,
            map=map_settings.model_copy(update={"installed": installed}),
            map_url="/map/active/" if installed else None,
            message=map_settings.last_error or message,
        )

    def install(self, server_id: str, server_running: bool = False) -> ServerInstance:
        if server_running:
            raise RuntimeError("stop_server_before_installing_map")

        server = self.instance_service.get_server(server_id)
        provider_version = self.resolve_provider_version(server)
        loader = self.server_type_to_loader(server.server_type)
        jar_relative_path = self._provider_jar_relative_path(loader)
        port = server.map.web_port or self._find_available_port(server.id)

        try:
            target = Path(server.server_dir) / jar_relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            self._download_file(provider_version.download_url, target)
            self._write_webserver_config(server, loader, port)
        except Exception as exc:
            failed = server.map.model_copy(
                update={
                    "enabled": True,
                    "provider": BLUEMAP_PROVIDER_ID,
                    "installed": False,
                    "needs_restart": False,
                    "web_port": port,
                    "bind_host": "127.0.0.1",
                    "jar_path": jar_relative_path.as_posix(),
                    "last_error": str(exc),
                }
            )
            self.instance_service.update_server_map(server.id, failed)
            raise

        map_settings = ServerMapSettings(
            enabled=True,
            provider=BLUEMAP_PROVIDER_ID,
            installed=True,
            needs_restart=True,
            web_port=port,
            bind_host="127.0.0.1",
            provider_version=provider_version.version_number,
            jar_path=jar_relative_path.as_posix(),
            last_error="",
        )
        return self.instance_service.update_server_map(server.id, map_settings)

    def reconfigure(self, server_id: str, server_running: bool = False) -> ServerInstance:
        if server_running:
            raise RuntimeError("stop_server_before_reconfiguring_map")
        server = self.instance_service.get_server(server_id)
        if not server.map.installed:
            raise RuntimeError("bluemap_not_installed")
        loader = self.server_type_to_loader(server.server_type)
        port = server.map.web_port or self._find_available_port(server.id)
        self._write_webserver_config(server, loader, port)
        updated = server.map.model_copy(
            update={
                "enabled": True,
                "provider": BLUEMAP_PROVIDER_ID,
                "needs_restart": True,
                "web_port": port,
                "bind_host": "127.0.0.1",
                "last_error": "",
            }
        )
        return self.instance_service.update_server_map(server.id, updated)

    def resolve_provider_version(self, server: ServerInstance) -> MapProviderVersion:
        if not server.minecraft_version:
            raise ValueError("minecraft_version_required_for_map_install")

        loader = self.server_type_to_loader(server.server_type)
        versions = self._fetch_bluemap_versions(server.minecraft_version, loader, featured=True)
        if not versions:
            versions = self._fetch_bluemap_versions(server.minecraft_version, loader, featured=False)
        version = self._select_provider_version(versions)
        if version is None:
            versions = self._fetch_bluemap_versions(None, loader, featured=None)
            matching_versions = [
                item
                for item in versions
                if self._version_matches_minecraft_version(item, server.minecraft_version)
            ]
            version = self._select_provider_version(matching_versions)
        if version is None:
            raise ValueError("compatible_bluemap_version_not_found")
        return version

    def proxy_active(self, path: str, query_string: bytes = b"") -> tuple[int, dict[str, str], bytes]:
        server = self.instance_service.get_active_server()
        if server is None:
            raise FileNotFoundError("active_server_not_selected")

        map_settings = self._normalized_map_settings(server)
        if not map_settings.enabled or not map_settings.installed:
            raise FileNotFoundError("bluemap_not_installed")
        if not map_settings.web_port:
            raise FileNotFoundError("bluemap_port_not_configured")

        url = self._proxy_url(map_settings, path, query_string)
        request = urllib.request.Request(url, headers={"User-Agent": "MinecraftWebPanel/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
                headers = self._proxy_headers(dict(response.headers.items()), path)
                return response.status, headers, response.read()
        except urllib.error.HTTPError as exc:
            headers = self._proxy_headers(dict(exc.headers.items()), path)
            return exc.code, headers, exc.read()
        except OSError as exc:
            raise ConnectionError(f"bluemap_proxy_unavailable: {exc}") from exc

    @staticmethod
    def server_type_to_loader(server_type: str) -> str:
        normalized = str(server_type or "").strip().lower()
        loader = SERVER_TYPE_TO_MODRINTH_LOADER.get(normalized)
        if not loader:
            raise ValueError("server_type_not_supported_for_bluemap")
        return loader

    @staticmethod
    def _select_provider_version(versions: list[dict[str, Any]]) -> MapProviderVersion | None:
        sorted_versions = sorted(
            versions,
            key=lambda item: str(item.get("date_published", "")),
            reverse=True,
        )
        for version in sorted_versions:
            files = version.get("files", [])
            if not isinstance(files, list):
                continue
            file_payload = next(
                (
                    item
                    for item in files
                    if item.get("primary") and str(item.get("filename", "")).lower().endswith(".jar")
                ),
                None,
            )
            if file_payload is None:
                file_payload = next(
                    (
                        item
                        for item in files
                        if str(item.get("filename", "")).lower().endswith(".jar")
                    ),
                    None,
                )
            if not file_payload or not file_payload.get("url"):
                continue
            return MapProviderVersion(
                version_number=str(version.get("version_number", "")),
                file_name=str(file_payload.get("filename", "BlueMap.jar")),
                download_url=str(file_payload["url"]),
                loaders=[str(item) for item in version.get("loaders", [])],
                game_versions=[str(item) for item in version.get("game_versions", [])],
            )
        return None

    def _fetch_bluemap_versions(
        self,
        minecraft_version: str | None,
        loader: str,
        featured: bool | None,
    ) -> list[dict[str, Any]]:
        params = {
            "loaders": json.dumps([loader]),
            "include_changelog": "false",
        }
        if minecraft_version:
            params["game_versions"] = json.dumps([minecraft_version])
        if featured is not None:
            params["featured"] = "true" if featured else "false"
        url = f"{MODRINTH_BLUEMAP_VERSIONS_URL}?{urllib.parse.urlencode(params)}"
        payload = self._request_json(url)
        return payload if isinstance(payload, list) else []

    @classmethod
    def _version_matches_minecraft_version(cls, version: dict[str, Any], minecraft_version: str) -> bool:
        requested = str(minecraft_version or "").strip()
        if not requested:
            return False
        for raw_tag in version.get("game_versions", []):
            tag = str(raw_tag).strip()
            if not tag:
                continue
            if tag == requested:
                return True
            if tag.endswith(".x") and requested.startswith(tag[:-1]):
                return True
            if cls._version_tag_is_family_match(tag, requested):
                return True
            if cls._version_tag_range_contains(tag, requested):
                return True
        return False

    @staticmethod
    def _version_tag_is_family_match(tag: str, requested: str) -> bool:
        tag_parts = tag.split(".")
        requested_parts = requested.split(".")
        if len(tag_parts) != 2 or len(requested_parts) < 2:
            return False
        return tag_parts == requested_parts[:2]

    @classmethod
    def _version_tag_range_contains(cls, tag: str, requested: str) -> bool:
        if " - " not in tag and "-" not in tag:
            return False
        delimiter = " - " if " - " in tag else "-"
        parts = [part.strip() for part in tag.split(delimiter, 1)]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return False
        requested_tuple = cls._minecraft_version_tuple(requested)
        lower = cls._minecraft_version_tuple(parts[0])
        upper = cls._minecraft_version_tuple(parts[1])
        if requested_tuple is None or lower is None or upper is None:
            return False
        return lower <= requested_tuple <= upper

    @staticmethod
    def _minecraft_version_tuple(value: str) -> tuple[int, ...] | None:
        parts: list[int] = []
        for part in value.split("."):
            if not part.isdigit():
                return None
            parts.append(int(part))
        return tuple(parts)

    def _request_json(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": "MinecraftWebPanel/0.1"})
        with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    def _download_file(self, url: str, target: Path) -> None:
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

    def _find_available_port(self, server_id: str) -> int:
        used_ports = {
            server.map.web_port
            for server in self.instance_service.list_servers()
            if server.id != server_id and server.map.web_port
        }
        for port in BLUEMAP_PORT_RANGE:
            if port in used_ports:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                if sock.connect_ex(("127.0.0.1", port)) != 0:
                    return port
        raise RuntimeError("no_available_bluemap_port")

    def _write_webserver_config(self, server: ServerInstance, loader: str, port: int) -> None:
        config_dir = self._bluemap_config_dir(server, loader)
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "webserver.conf").write_text(
            "\n".join(
                [
                    "enabled: true",
                    'webroot: "bluemap/web"',
                    'ip: "127.0.0.1"',
                    f"port: {port}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _provider_jar_relative_path(loader: str) -> Path:
        directory = "mods" if loader in MOD_LOADERS else "plugins"
        return Path(directory) / "BlueMap.jar"

    @staticmethod
    def _bluemap_config_dir(server: ServerInstance, loader: str) -> Path:
        server_dir = Path(server.server_dir)
        if loader in MOD_LOADERS or loader == "sponge":
            return server_dir / "config" / "bluemap"
        return server_dir / "plugins" / "BlueMap"

    @staticmethod
    def _normalized_map_settings(server: ServerInstance) -> ServerMapSettings:
        map_settings = server.map
        if map_settings.jar_path:
            return map_settings
        try:
            loader = BlueMapIntegrationService.server_type_to_loader(server.server_type)
        except ValueError:
            return map_settings
        return map_settings.model_copy(
            update={"jar_path": BlueMapIntegrationService._provider_jar_relative_path(loader).as_posix()}
        )

    @staticmethod
    def _jar_exists(server: ServerInstance, map_settings: ServerMapSettings) -> bool:
        if not map_settings.jar_path:
            return False
        target = (Path(server.server_dir) / map_settings.jar_path).resolve()
        server_dir = Path(server.server_dir).resolve()
        try:
            target.relative_to(server_dir)
        except ValueError:
            return False
        return target.is_file()

    @staticmethod
    def _webserver_responds(map_settings: ServerMapSettings) -> bool:
        if not map_settings.web_port:
            return False
        try:
            with socket.create_connection(
                (map_settings.bind_host, map_settings.web_port),
                timeout=0.2,
            ):
                return True
        except OSError:
            return False

    @staticmethod
    def _proxy_url(map_settings: ServerMapSettings, path: str, query_string: bytes) -> str:
        if map_settings.bind_host not in {"127.0.0.1", "localhost", "::1"}:
            raise ConnectionError("bluemap_proxy_host_must_be_local")
        safe_path = urllib.parse.quote(str(path or ""), safe="/:@!$&'()*+,;=-._~")
        host = f"[{map_settings.bind_host}]" if ":" in map_settings.bind_host else map_settings.bind_host
        url = f"http://{host}:{map_settings.web_port}/{safe_path}"
        if query_string:
            url = f"{url}?{query_string.decode('latin-1')}"
        return url

    @staticmethod
    def _proxy_headers(headers: dict[str, str], path: str) -> dict[str, str]:
        forwarded = {}
        for key, value in headers.items():
            if key.lower() in {"content-type", "cache-control", "content-encoding", "etag", "last-modified"}:
                forwarded[key] = value
        if not any(key.lower() == "content-type" for key in forwarded):
            guessed, _ = mimetypes.guess_type(path)
            forwarded["Content-Type"] = guessed or "application/octet-stream"
        return forwarded
