from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import get_instance_service, get_log_buffer, get_manager
from app.models.server import (
    ConsoleCommandRequest,
    CreateServerInstanceRequest,
    ServerInstance,
    UpdateServerInstanceRequest,
)

router = APIRouter(prefix="/api/servers", tags=["servers"])


@router.get("", response_model=list[ServerInstance])
async def list_servers(request: Request) -> list[ServerInstance]:
    return get_instance_service(request).list_servers()


@router.post("", response_model=ServerInstance, status_code=status.HTTP_201_CREATED)
async def create_server(request: Request, payload: CreateServerInstanceRequest) -> ServerInstance:
    try:
        return get_instance_service(request).create_server(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/active", response_model=ServerInstance | None)
async def get_active_server(request: Request) -> ServerInstance | None:
    return get_instance_service(request).get_active_server()


@router.post("/{server_id}/activate", response_model=ServerInstance)
async def activate_server(request: Request, server_id: str) -> ServerInstance:
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
async def get_server(request: Request, server_id: str) -> ServerInstance:
    try:
        return get_instance_service(request).get_server(server_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc


@router.patch("/{server_id}", response_model=ServerInstance)
async def update_server(
    request: Request,
    server_id: str,
    payload: UpdateServerInstanceRequest,
) -> ServerInstance:
    try:
        return get_instance_service(request).update_server(server_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(request: Request, server_id: str, delete_files: bool = False) -> None:
    if get_manager(request).is_running() and get_instance_service(request).active_server_id == server_id:
        raise HTTPException(status_code=409, detail="running_active_server_cannot_be_deleted")
    try:
        get_instance_service(request).delete_server(server_id, delete_files=delete_files)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc


@router.post("/active/start")
async def start_active_server(request: Request) -> dict:
    try:
        await get_manager(request).start()
        return get_manager(request).get_status()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/active/stop")
async def stop_active_server(request: Request) -> dict:
    await get_manager(request).stop()
    return get_manager(request).get_status()


@router.post("/active/restart")
async def restart_active_server(request: Request) -> dict:
    try:
        await get_manager(request).restart()
        return get_manager(request).get_status()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/active/kill")
async def kill_active_server(request: Request) -> dict:
    await get_manager(request).kill()
    return get_manager(request).get_status()


@router.get("/active/status")
async def get_active_status(request: Request) -> dict:
    return get_manager(request).get_status()


@router.get("/active/work-data")
async def get_active_work_data(request: Request) -> dict:
    return get_manager(request).get_work_data()


@router.get("/active/metrics")
async def get_active_metrics(request: Request) -> dict:
    return get_manager(request).get_metrics()


@router.get("/active/logs/recent")
async def get_recent_logs(request: Request, limit: int = 300) -> dict:
    return {"items": get_log_buffer(request).recent(limit=limit)}


@router.post("/active/console/command")
async def send_console_command(request: Request, payload: ConsoleCommandRequest) -> dict:
    try:
        await get_manager(request).send_stdin_command(payload.command)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"accepted": True}

