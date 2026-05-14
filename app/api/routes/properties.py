from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user, get_instance_service, get_manager, get_properties_service, require_permission
from app.models.auth import AuthUser
from app.models.properties import ServerPropertiesResponse, UpdateServerPropertiesRequest

router = APIRouter(prefix="/api/servers/active/properties", tags=["properties"])


def _active_server(request: Request):
    server = get_instance_service(request).get_active_server()
    if server is None:
        raise HTTPException(status_code=404, detail="active_server_not_selected")
    return server


@router.get("", response_model=ServerPropertiesResponse)
async def read_active_properties(
    request: Request,
    current_user: AuthUser = Depends(require_permission("properties.view")),
) -> ServerPropertiesResponse:
    return get_properties_service(request).read(_active_server(request))


@router.put("", response_model=ServerPropertiesResponse)
async def update_active_properties(
    request: Request,
    payload: UpdateServerPropertiesRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> ServerPropertiesResponse:
    if get_manager(request).is_running():
        raise HTTPException(status_code=409, detail="properties_cannot_be_changed_while_running")
    if payload.raw is not None and not current_user.has_permission("properties.raw_edit"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission_denied")
    if payload.values is not None and not current_user.has_permission("properties.quick_edit"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission_denied")
    try:
        service = get_properties_service(request)
        server = _active_server(request)
        if payload.raw is not None:
            return service.write_raw(server, payload.raw)
        if payload.values is not None:
            return service.update_values(server, payload.values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail="values_or_raw_required")
