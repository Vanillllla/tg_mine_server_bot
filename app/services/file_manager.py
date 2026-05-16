import shutil
from zipfile import ZIP_DEFLATED, ZipFile
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import UploadFile

from app.models.server import ServerInstance


TEXT_EXTENSIONS = {
    ".json",
    ".log",
    ".properties",
    ".txt",
    ".yml",
    ".yaml",
    ".cfg",
    ".conf",
    ".toml",
    ".ini",
}

CLIENT_MODS_DIR = "client-mods"
UPLOAD_COPY_CHUNK_SIZE = 8 * 1024 * 1024


class FileManagerService:
    def list_dir(self, server: ServerInstance, relative_path: str = "") -> dict[str, Any]:
        root = self._root(server)
        if not relative_path:
            root.mkdir(parents=True, exist_ok=True)
        target = self._resolve(server, relative_path)
        if not target.exists():
            raise FileNotFoundError("path_not_found")
        if not target.is_dir():
            raise NotADirectoryError("path_is_not_directory")

        items = []
        for child in sorted(target.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower())):
            stat = child.stat()
            items.append(
                {
                    "name": child.name,
                    "path": self._relative(root, child),
                    "type": "directory" if child.is_dir() else "file",
                    "size": stat.st_size,
                    "modified_at": stat.st_mtime,
                    "editable": self._is_editable(child),
                }
            )
        return {"path": self._relative(root, target), "items": items}

    def read_text(self, server: ServerInstance, relative_path: str) -> dict[str, Any]:
        target = self._resolve(server, relative_path)
        if not target.is_file():
            raise FileNotFoundError("file_not_found")
        if not self._is_editable(target):
            raise ValueError("file_type_is_not_editable")
        return {
            "path": self._relative(self._root(server), target),
            "content": target.read_text(encoding="utf-8", errors="replace"),
        }

    def write_text(self, server: ServerInstance, relative_path: str, content: str) -> dict[str, Any]:
        target = self._resolve(server, relative_path)
        if target.exists() and not target.is_file():
            raise ValueError("path_is_not_file")
        if not self._is_editable(target):
            raise ValueError("file_type_is_not_editable")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": self._relative(self._root(server), target), "saved": True}

    def mkdir(self, server: ServerInstance, relative_path: str, name: str) -> dict[str, Any]:
        if not self._valid_name(name):
            raise ValueError("invalid_directory_name")
        target = self._resolve(server, str(Path(relative_path) / name))
        target.mkdir(parents=False, exist_ok=False)
        return {"path": self._relative(self._root(server), target), "created": True}

    async def upload(self, server: ServerInstance, relative_path: str, file: UploadFile) -> dict[str, Any]:
        if not file.filename or not self._valid_name(file.filename):
            raise ValueError("invalid_file_name")
        directory = self._resolve(server, relative_path)
        if not directory.is_dir():
            raise NotADirectoryError("path_is_not_directory")
        target = self._resolve(server, str(Path(relative_path) / file.filename))
        with target.open("wb") as output:
            while chunk := await file.read(UPLOAD_COPY_CHUNK_SIZE):
                output.write(chunk)
        return {"path": self._relative(self._root(server), target), "uploaded": True}

    def delete(self, server: ServerInstance, relative_path: str) -> dict[str, Any]:
        target = self._resolve(server, relative_path)
        if target == self._root(server):
            raise ValueError("cannot_delete_server_root")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        else:
            raise FileNotFoundError("path_not_found")
        return {"deleted": True}

    def rename(self, server: ServerInstance, relative_path: str, new_name: str) -> dict[str, Any]:
        if not self._valid_name(new_name):
            raise ValueError("invalid_name")
        source = self._resolve(server, relative_path)
        if source == self._root(server):
            raise ValueError("cannot_rename_server_root")
        if not source.exists():
            raise FileNotFoundError("path_not_found")
        target = self._resolve(server, str(Path(relative_path).parent / new_name))
        source.rename(target)
        return {"path": self._relative(self._root(server), target), "renamed": True}

    def ensure_client_mods_dir(self, server: ServerInstance) -> dict[str, Any]:
        target = self._resolve(server, CLIENT_MODS_DIR)
        if target.exists() and not target.is_dir():
            raise ValueError("client_mods_path_is_not_directory")
        target.mkdir(parents=True, exist_ok=True)
        return self.client_mods_info(server)

    def client_mods_info(self, server: ServerInstance) -> dict[str, Any]:
        target = self._resolve(server, CLIENT_MODS_DIR)
        if not target.exists():
            return {
                "path": CLIENT_MODS_DIR,
                "exists": False,
                "files_count": 0,
                "size": 0,
            }
        if not target.is_dir():
            raise ValueError("client_mods_path_is_not_directory")

        files = [path for path in target.rglob("*") if path.is_file()]
        return {
            "path": CLIENT_MODS_DIR,
            "exists": True,
            "files_count": len(files),
            "size": sum(path.stat().st_size for path in files),
        }

    def write_client_mods_archive(self, server: ServerInstance, archive_path: Path) -> dict[str, Any]:
        target = self._resolve(server, CLIENT_MODS_DIR)
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
        if not target.is_dir():
            raise ValueError("client_mods_path_is_not_directory")

        files_count = 0
        with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(target.rglob("*"), key=lambda item: item.as_posix().lower()):
                if not path.is_file():
                    continue
                archive.write(path, path.relative_to(target).as_posix())
                files_count += 1
        return {"files_count": files_count, "size": archive_path.stat().st_size}

    @staticmethod
    def _root(server: ServerInstance) -> Path:
        return Path(server.server_dir).expanduser().resolve()

    def _resolve(self, server: ServerInstance, relative_path: str) -> Path:
        root = self._root(server)
        relative = self._normalize_relative_path(relative_path)
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("path_must_stay_inside_server_dir") from exc
        return target

    @staticmethod
    def _normalize_relative_path(relative_path: str) -> Path:
        normalized = PurePosixPath(str(relative_path or "").replace("\\", "/"))
        if normalized.is_absolute() or any(part == ".." or part.endswith(":") for part in normalized.parts):
            raise ValueError("path_must_stay_inside_server_dir")
        parts = [part for part in normalized.parts if part not in {"", "."}]
        return Path(*parts) if parts else Path()

    @staticmethod
    def _relative(root: Path, target: Path) -> str:
        value = target.resolve().relative_to(root.resolve()).as_posix()
        return "" if value == "." else value

    @staticmethod
    def _is_editable(path: Path) -> bool:
        return path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"eula.txt", "ops.json", "whitelist.json"}

    @staticmethod
    def _valid_name(name: str) -> bool:
        return bool(name and name not in {".", ".."} and "/" not in name and "\\" not in name)
