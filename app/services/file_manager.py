import shutil
from pathlib import Path
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


class FileManagerService:
    def list_dir(self, server: ServerInstance, relative_path: str = "") -> dict[str, Any]:
        root = self._root(server)
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
            while chunk := await file.read(1024 * 1024):
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

    @staticmethod
    def _root(server: ServerInstance) -> Path:
        return Path(server.server_dir).expanduser().resolve()

    def _resolve(self, server: ServerInstance, relative_path: str) -> Path:
        root = self._root(server)
        target = (root / relative_path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("path_must_stay_inside_server_dir") from exc
        return target

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
