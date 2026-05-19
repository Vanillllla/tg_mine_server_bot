from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_panel_settings_service, get_telegram_bot_service, require_admin
from app.models.auth import AuthUser
from app.models.settings import (
    DomainSettings,
    EmptyShutdownSettings,
    JavaRuntime,
    PublicPanelSettings,
    SetDefaultJavaRuntimeRequest,
    TelegramSettings,
    TelegramSettingsResponse,
    UpsertJavaRuntimeRequest,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/public", response_model=PublicPanelSettings)
async def get_public_settings(request: Request) -> PublicPanelSettings:
    return get_panel_settings_service(request).public_settings()


@router.get("/empty-shutdown", response_model=EmptyShutdownSettings)
async def get_empty_shutdown_settings(
    request: Request,
    current_user: AuthUser = Depends(require_admin),
) -> EmptyShutdownSettings:
    return get_panel_settings_service(request).empty_shutdown_settings()


@router.put("/empty-shutdown", response_model=EmptyShutdownSettings)
async def update_empty_shutdown_settings(
    request: Request,
    payload: EmptyShutdownSettings,
    current_user: AuthUser = Depends(require_admin),
) -> EmptyShutdownSettings:
    return get_panel_settings_service(request).update_empty_shutdown_settings(payload)


@router.get("/domains", response_model=DomainSettings)
async def get_domain_settings(
    request: Request,
    current_user: AuthUser = Depends(require_admin),
) -> DomainSettings:
    return get_panel_settings_service(request).domain_settings()


@router.put("/domains", response_model=DomainSettings)
async def update_domain_settings(
    request: Request,
    payload: DomainSettings,
    current_user: AuthUser = Depends(require_admin),
) -> DomainSettings:
    return get_panel_settings_service(request).update_domain_settings(payload)


def _telegram_settings_response(request: Request) -> TelegramSettingsResponse:
    settings = get_panel_settings_service(request).telegram_settings()
    status = get_telegram_bot_service(request).status()
    return TelegramSettingsResponse(
        **settings.model_dump(),
        running=bool(status["running"]),
        status=str(status["status"]),
        last_error=str(status["last_error"]),
    )


@router.get("/telegram", response_model=TelegramSettingsResponse)
async def get_telegram_settings(
    request: Request,
    current_user: AuthUser = Depends(require_admin),
) -> TelegramSettingsResponse:
    return _telegram_settings_response(request)


@router.put("/telegram", response_model=TelegramSettingsResponse)
async def update_telegram_settings(
    request: Request,
    payload: TelegramSettings,
    current_user: AuthUser = Depends(require_admin),
) -> TelegramSettingsResponse:
    get_panel_settings_service(request).update_telegram_settings(payload)
    try:
        await get_telegram_bot_service(request).apply_settings(raise_errors=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _telegram_settings_response(request)


@router.post("/telegram/stop", response_model=TelegramSettingsResponse)
async def stop_telegram_bot(
    request: Request,
    current_user: AuthUser = Depends(require_admin),
) -> TelegramSettingsResponse:
    service = get_panel_settings_service(request)
    settings = service.telegram_settings()
    service.update_telegram_settings(
        TelegramSettings(
            autostart=False,
            bot_token=settings.bot_token,
            admin_ids=settings.admin_ids,
        )
    )
    await get_telegram_bot_service(request).stop(clear_error=True)
    return _telegram_settings_response(request)


@router.get("/java-runtimes", response_model=list[JavaRuntime])
async def list_java_runtimes(
    request: Request,
    current_user: AuthUser = Depends(require_admin),
) -> list[JavaRuntime]:
    return get_panel_settings_service(request).list_java_runtimes()


@router.post("/java-runtimes", response_model=JavaRuntime)
async def upsert_java_runtime(
    request: Request,
    payload: UpsertJavaRuntimeRequest,
    current_user: AuthUser = Depends(require_admin),
) -> JavaRuntime:
    return get_panel_settings_service(request).upsert_java_runtime(payload)


@router.post("/java-runtimes/default", response_model=JavaRuntime)
async def set_default_java_runtime(
    request: Request,
    payload: SetDefaultJavaRuntimeRequest,
    current_user: AuthUser = Depends(require_admin),
) -> JavaRuntime:
    try:
        return get_panel_settings_service(request).set_default_java_runtime(payload.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="java_runtime_not_found") from exc
