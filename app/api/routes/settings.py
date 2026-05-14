from fastapi import APIRouter, HTTPException, Request

from app.api.deps import get_panel_settings_service
from app.models.settings import (
    JavaRuntime,
    SetDefaultJavaRuntimeRequest,
    UpsertJavaRuntimeRequest,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/java-runtimes", response_model=list[JavaRuntime])
async def list_java_runtimes(request: Request) -> list[JavaRuntime]:
    return get_panel_settings_service(request).list_java_runtimes()


@router.post("/java-runtimes", response_model=JavaRuntime)
async def upsert_java_runtime(
    request: Request,
    payload: UpsertJavaRuntimeRequest,
) -> JavaRuntime:
    return get_panel_settings_service(request).upsert_java_runtime(payload)


@router.post("/java-runtimes/default", response_model=JavaRuntime)
async def set_default_java_runtime(
    request: Request,
    payload: SetDefaultJavaRuntimeRequest,
) -> JavaRuntime:
    try:
        return get_panel_settings_service(request).set_default_java_runtime(payload.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="java_runtime_not_found") from exc
