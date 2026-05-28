from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.api.deps import get_instance_service, get_manager, get_map_service, require_permission
from app.models.auth import AuthUser
from app.models.map import MapInstallRequest, MapStatusResponse
from app.models.server import ServerInstance

router = APIRouter(tags=["map"])


def _server_is_running(request: Request, server_id: str) -> bool:
    manager = get_manager(request)
    return manager.is_running() and (
        manager.current_server_id == server_id
        or get_instance_service(request).active_server_id == server_id
    )


def _get_server_or_404(request: Request, server_id: str) -> ServerInstance:
    try:
        return get_instance_service(request).get_server(server_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc


@router.get("/api/map/providers")
async def list_map_providers(
    request: Request,
    current_user: AuthUser = Depends(require_permission("map.view")),
) -> dict:
    return {"items": get_map_service(request).providers()}


@router.get("/api/servers/{server_id}/map/status", response_model=MapStatusResponse)
async def get_server_map_status(
    request: Request,
    server_id: str,
    current_user: AuthUser = Depends(require_permission("map.view")),
) -> MapStatusResponse:
    return get_map_service(request).status(_get_server_or_404(request, server_id))


@router.post("/api/servers/{server_id}/map/install", response_model=MapStatusResponse)
async def install_server_map(
    request: Request,
    server_id: str,
    payload: MapInstallRequest | None = None,
    current_user: AuthUser = Depends(require_permission("map.manage")),
) -> MapStatusResponse:
    try:
        server = get_map_service(request).install(
            server_id,
            server_running=_server_is_running(request, server_id),
            provider=payload.provider if payload is not None else "bluemap",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"bluemap_install_failed: {exc}") from exc
    return get_map_service(request).status(server)


@router.post("/api/servers/{server_id}/map/reconfigure", response_model=MapStatusResponse)
async def reconfigure_server_map(
    request: Request,
    server_id: str,
    current_user: AuthUser = Depends(require_permission("map.manage")),
) -> MapStatusResponse:
    try:
        server = get_map_service(request).reconfigure(
            server_id,
            server_running=_server_is_running(request, server_id),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_map_service(request).status(server)


@router.get("/map/active", include_in_schema=False)
@router.get("/map/active/{path:path}", include_in_schema=False)
async def proxy_active_map(
    request: Request,
    path: str = "",
    current_user: AuthUser = Depends(require_permission("map.view")),
) -> Response:
    try:
        query_string = request.scope.get("query_string", b"")
        status_code, headers, body = get_map_service(request).proxy_active(path, query_string)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=body, status_code=status_code, headers=headers)
