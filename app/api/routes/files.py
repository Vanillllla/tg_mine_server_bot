from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_file_manager, get_instance_service
from app.models.files import CreateDirectoryRequest, RenamePathRequest, WriteTextFileRequest

router = APIRouter(prefix="/api/servers/active/files", tags=["files"])


def _active_server(request: Request):
    server = get_instance_service(request).get_active_server()
    if server is None:
        raise HTTPException(status_code=404, detail="active_server_not_selected")
    return server


def _handle_file_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, NotADirectoryError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, FileExistsError):
        return HTTPException(status_code=409, detail="path_already_exists")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="file_manager_error")


@router.get("")
async def list_active_files(request: Request, path: str = "") -> dict:
    try:
        return get_file_manager(request).list_dir(_active_server(request), path)
    except Exception as exc:
        raise _handle_file_error(exc) from exc


@router.get("/text")
async def read_active_text_file(request: Request, path: str) -> dict:
    try:
        return get_file_manager(request).read_text(_active_server(request), path)
    except Exception as exc:
        raise _handle_file_error(exc) from exc


@router.put("/text")
async def write_active_text_file(request: Request, path: str, payload: WriteTextFileRequest) -> dict:
    try:
        return get_file_manager(request).write_text(_active_server(request), path, payload.content)
    except Exception as exc:
        raise _handle_file_error(exc) from exc


@router.post("/directories")
async def create_active_directory(
    request: Request,
    payload: CreateDirectoryRequest,
    path: str = "",
) -> dict:
    try:
        return get_file_manager(request).mkdir(_active_server(request), path, payload.name)
    except Exception as exc:
        raise _handle_file_error(exc) from exc


@router.post("/upload")
async def upload_active_file(
    request: Request,
    path: str = "",
    file: UploadFile = File(...),
) -> dict:
    try:
        return await get_file_manager(request).upload(_active_server(request), path, file)
    except Exception as exc:
        raise _handle_file_error(exc) from exc


@router.get("/download")
async def download_active_file(request: Request, path: str) -> FileResponse:
    try:
        target = get_file_manager(request)._resolve(_active_server(request), path)
        if not target.is_file():
            raise FileNotFoundError("file_not_found")
        return FileResponse(target, filename=target.name)
    except Exception as exc:
        raise _handle_file_error(exc) from exc


@router.delete("")
async def delete_active_path(request: Request, path: str) -> dict:
    try:
        return get_file_manager(request).delete(_active_server(request), path)
    except Exception as exc:
        raise _handle_file_error(exc) from exc


@router.patch("")
async def rename_active_path(request: Request, path: str, payload: RenamePathRequest) -> dict:
    try:
        return get_file_manager(request).rename(_active_server(request), path, payload.new_name)
    except Exception as exc:
        raise _handle_file_error(exc) from exc
