import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.api.deps import get_file_manager, get_instance_service, require_permission
from app.models.auth import AuthUser

router = APIRouter(prefix="/api/servers/active/client-mods", tags=["client-mods"])


def _active_server(request: Request):
    server = get_instance_service(request).get_active_server()
    if server is None:
        raise HTTPException(status_code=404, detail="active_server_not_selected")
    return server


def _handle_client_mods_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="client_mods_error")


@router.get("")
async def get_client_mods_info(
    request: Request,
    current_user: AuthUser = Depends(require_permission("client_mods.download")),
) -> dict:
    try:
        return get_file_manager(request).client_mods_info(_active_server(request))
    except Exception as exc:
        raise _handle_client_mods_error(exc) from exc


@router.post("/ensure")
async def ensure_client_mods_folder(
    request: Request,
    current_user: AuthUser = Depends(require_permission("files.upload")),
) -> dict:
    try:
        return get_file_manager(request).ensure_client_mods_dir(_active_server(request))
    except Exception as exc:
        raise _handle_client_mods_error(exc) from exc


@router.get("/archive")
async def download_client_mods_archive(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(require_permission("client_mods.download")),
) -> FileResponse:
    server = _active_server(request)
    safe_server_id = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in server.id)
    fd, archive_name = tempfile.mkstemp(prefix=f"{safe_server_id}-client-mods-", suffix=".zip")
    os.close(fd)
    try:
        get_file_manager(request).write_client_mods_archive(server, Path(archive_name))
        background_tasks.add_task(Path(archive_name).unlink, missing_ok=True)
        return FileResponse(
            archive_name,
            background=background_tasks,
            media_type="application/zip",
            filename=f"{safe_server_id}-client-mods.zip",
        )
    except Exception as exc:
        Path(archive_name).unlink(missing_ok=True)
        raise _handle_client_mods_error(exc) from exc
