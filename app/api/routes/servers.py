from pathlib import Path
from zipfile import BadZipFile, ZipFile, ZipInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.api.deps import get_instance_service, get_log_buffer, get_manager, require_permission
from app.models.auth import AuthUser
from app.models.server import (
    ConsoleCommandRequest,
    CreateServerInstanceRequest,
    ServerInstance,
    UpdateServerInstanceRequest,
)

router = APIRouter(prefix="/api/servers", tags=["servers"])


def _safe_active_server_payload(payload: dict | None, current_user: AuthUser) -> dict | None:
    if payload is None or current_user.has_permission("servers.view"):
        return payload
    return {
        "id": payload.get("id"),
        "display_name": payload.get("display_name"),
        "minecraft_version": payload.get("minecraft_version", ""),
        "server_type": payload.get("server_type", ""),
    }


def _safe_archive_entries(archive: ZipFile) -> list[tuple[ZipInfo, Path]]:
    raw_names = [info.filename.replace("\\", "/") for info in archive.infolist() if info.filename]
    roots = {Path(name).parts[0] for name in raw_names if Path(name).parts}
    strip_root = len(roots) == 1

    entries: list[tuple[ZipInfo, Path]] = []
    for info in archive.infolist():
        normalized = info.filename.replace("\\", "/")
        path = Path(normalized)
        parts = path.parts[1:] if strip_root else path.parts
        if not parts:
            continue
        if path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("archive_contains_unsafe_path")
        relative = Path(*parts)
        if relative.is_absolute():
            raise ValueError("archive_contains_unsafe_path")
        entries.append((info, relative))
    return entries


def _choose_jar_file(entries: list[tuple[ZipInfo, Path]], requested: str = "") -> str:
    if requested:
        candidate = Path(requested)
        if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
            raise ValueError("jar_file_has_unsafe_path")
        if any(relative.as_posix() == candidate.as_posix() for info, relative in entries if not info.is_dir()):
            return candidate.as_posix()
        raise ValueError("jar_file_not_found_in_archive")

    jars = [relative for info, relative in entries if not info.is_dir() and relative.suffix.lower() == ".jar"]
    if not jars:
        raise ValueError("archive_must_contain_jar_file")

    priority = ("forge", "paper", "spigot", "fabric", "server")
    jars.sort(
        key=lambda path: (
            1 if any(token in path.name.lower() for token in ("installer", "client", "sources")) else 0,
            next((index for index, token in enumerate(priority) if token in path.name.lower()), 999),
            len(path.parts),
            path.name.lower(),
        )
    )
    return jars[0].as_posix()


def _extract_archive(archive: ZipFile, entries: list[tuple[ZipInfo, Path]], target_dir: Path) -> None:
    root = target_dir.resolve()
    for info, relative in entries:
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("archive_contains_unsafe_path") from exc

        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, target.open("wb") as output:
            while chunk := source.read(1024 * 1024):
                output.write(chunk)


@router.get("", response_model=list[ServerInstance])
async def list_servers(
    request: Request,
    current_user: AuthUser = Depends(require_permission("servers.view")),
) -> list[ServerInstance]:
    return get_instance_service(request).list_servers()


@router.post("", response_model=ServerInstance, status_code=status.HTTP_201_CREATED)
async def create_server(
    request: Request,
    payload: CreateServerInstanceRequest,
    current_user: AuthUser = Depends(require_permission("servers.create")),
) -> ServerInstance:
    try:
        return get_instance_service(request).create_server(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload-core", response_model=ServerInstance, status_code=status.HTTP_201_CREATED)
async def create_server_from_uploaded_core(
    request: Request,
    id: str = Form(...),
    display_name: str = Form(...),
    minecraft_version: str = Form(""),
    server_type: str = Form("custom"),
    java_path: str = Form("java"),
    xms_mb: int = Form(512),
    xmx_mb: int = Form(1024),
    eula_accept: bool = Form(False),
    core_file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_permission("files.upload_core")),
) -> ServerInstance:
    if not core_file.filename:
        raise HTTPException(status_code=400, detail="core_file_required")
    jar_name = Path(core_file.filename).name
    if jar_name != core_file.filename or not jar_name.lower().endswith(".jar"):
        raise HTTPException(status_code=400, detail="core_file_must_be_jar")

    service = get_instance_service(request)
    payload = CreateServerInstanceRequest(
        id=id,
        display_name=display_name,
        jar_file=jar_name,
        minecraft_version=minecraft_version,
        server_type=server_type or "custom",
        java_path=java_path or "java",
        xms_mb=xms_mb,
        xmx_mb=xmx_mb,
        eula_accept=eula_accept,
    )

    created_server_id = ""
    try:
        server = service.create_server(payload)
        created_server_id = server.id
        jar_path = Path(server.server_dir) / server.jar_file
        with jar_path.open("xb") as output:
            while chunk := await core_file.read(1024 * 1024):
                output.write(chunk)
        return server
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileExistsError as exc:
        if created_server_id:
            service.delete_server(created_server_id, delete_files=True)
        raise HTTPException(status_code=409, detail="core_file_already_exists") from exc
    except Exception:
        if created_server_id:
            service.delete_server(created_server_id, delete_files=True)
        raise


@router.post("/import-archive", response_model=ServerInstance, status_code=status.HTTP_201_CREATED)
async def create_server_from_archive(
    request: Request,
    id: str = Form(...),
    display_name: str = Form(...),
    minecraft_version: str = Form(""),
    server_type: str = Form("custom"),
    java_path: str = Form("java"),
    xms_mb: int = Form(512),
    xmx_mb: int = Form(1024),
    eula_accept: bool = Form(False),
    jar_file: str = Form(""),
    archive_file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_permission("servers.import")),
) -> ServerInstance:
    if not archive_file.filename or not archive_file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="archive_file_must_be_zip")

    service = get_instance_service(request)
    temp_archive_path = service.settings.uploads_dir / "temp" / f"{id}.import.zip"
    temp_archive_path.parent.mkdir(parents=True, exist_ok=True)

    created_server_id = ""
    try:
        with temp_archive_path.open("wb") as output:
            while chunk := await archive_file.read(1024 * 1024):
                output.write(chunk)

        with ZipFile(temp_archive_path) as archive:
            entries = _safe_archive_entries(archive)
            selected_jar = _choose_jar_file(entries, jar_file.strip())
            payload = CreateServerInstanceRequest(
                id=id,
                display_name=display_name,
                jar_file=selected_jar,
                minecraft_version=minecraft_version,
                server_type=server_type or "custom",
                java_path=java_path or "java",
                xms_mb=xms_mb,
                xmx_mb=xmx_mb,
                eula_accept=eula_accept,
            )
            server = service.create_server(payload)
            created_server_id = server.id
            _extract_archive(archive, entries, Path(server.server_dir))
            return server
    except BadZipFile as exc:
        raise HTTPException(status_code=400, detail="archive_file_is_not_valid_zip") from exc
    except ValueError as exc:
        if created_server_id:
            service.delete_server(created_server_id, delete_files=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        if created_server_id:
            service.delete_server(created_server_id, delete_files=True)
        raise
    finally:
        temp_archive_path.unlink(missing_ok=True)


@router.get("/active", response_model=ServerInstance | None)
async def get_active_server(
    request: Request,
    current_user: AuthUser = Depends(require_permission("servers.view")),
) -> ServerInstance | None:
    return get_instance_service(request).get_active_server()


@router.post("/{server_id}/activate", response_model=ServerInstance)
async def activate_server(
    request: Request,
    server_id: str,
    current_user: AuthUser = Depends(require_permission("servers.activate")),
) -> ServerInstance:
    manager = get_manager(request)
    if manager.is_running():
        raise HTTPException(
            status_code=409,
            detail="active_server_cannot_be_changed_while_running",
        )
    try:
        return get_instance_service(request).activate_server(server_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc


@router.get("/{server_id}", response_model=ServerInstance)
async def get_server(
    request: Request,
    server_id: str,
    current_user: AuthUser = Depends(require_permission("servers.view")),
) -> ServerInstance:
    try:
        return get_instance_service(request).get_server(server_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc


@router.patch("/{server_id}", response_model=ServerInstance)
async def update_server(
    request: Request,
    server_id: str,
    payload: UpdateServerInstanceRequest,
    current_user: AuthUser = Depends(require_permission("servers.edit_launch_settings")),
) -> ServerInstance:
    try:
        return get_instance_service(request).update_server(server_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    request: Request,
    server_id: str,
    delete_files: bool = True,
    current_user: AuthUser = Depends(require_permission("servers.delete")),
) -> None:
    if get_manager(request).is_running() and get_instance_service(request).active_server_id == server_id:
        raise HTTPException(status_code=409, detail="running_active_server_cannot_be_deleted")
    try:
        get_instance_service(request).delete_server(server_id, delete_files=delete_files)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc


@router.post("/active/start")
async def start_active_server(
    request: Request,
    current_user: AuthUser = Depends(require_permission("server.start")),
) -> dict:
    try:
        await get_manager(request).start()
        return get_manager(request).get_status()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/active/stop")
async def stop_active_server(
    request: Request,
    current_user: AuthUser = Depends(require_permission("server.stop")),
) -> dict:
    await get_manager(request).stop()
    return get_manager(request).get_status()


@router.post("/active/restart")
async def restart_active_server(
    request: Request,
    current_user: AuthUser = Depends(require_permission("server.restart")),
) -> dict:
    try:
        await get_manager(request).restart()
        return get_manager(request).get_status()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/active/kill")
async def kill_active_server(
    request: Request,
    current_user: AuthUser = Depends(require_permission("server.kill")),
) -> dict:
    await get_manager(request).kill()
    return get_manager(request).get_status()


@router.get("/active/status")
async def get_active_status(
    request: Request,
    current_user: AuthUser = Depends(require_permission("server.view_status")),
) -> dict:
    return get_manager(request).get_status()


@router.get("/active/work-data")
async def get_active_work_data(
    request: Request,
    current_user: AuthUser = Depends(require_permission("server.view_status")),
) -> dict:
    data = get_manager(request).get_work_data()
    data["active_server"] = _safe_active_server_payload(data.get("active_server"), current_user)
    if not current_user.has_permission("console.view"):
        data["recent_logs"] = []
    return data


@router.get("/active/metrics")
async def get_active_metrics(
    request: Request,
    current_user: AuthUser = Depends(require_permission("server.view_metrics")),
) -> dict:
    return get_manager(request).get_metrics()


@router.get("/active/logs/recent")
async def get_recent_logs(
    request: Request,
    limit: int = 300,
    current_user: AuthUser = Depends(require_permission("console.view")),
) -> dict:
    return {"items": get_log_buffer(request).recent(limit=limit)}


@router.post("/active/console/command")
async def send_console_command(
    request: Request,
    payload: ConsoleCommandRequest,
    current_user: AuthUser = Depends(require_permission("console.send_command")),
) -> dict:
    try:
        await get_manager(request).send_stdin_command(payload.command)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"accepted": True}
