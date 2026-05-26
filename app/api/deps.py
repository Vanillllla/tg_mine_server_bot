from typing import cast

from fastapi import HTTPException, Request, status

from app.core.settings import AppSettings
from app.models.auth import AuthUser
from app.services.auth import SESSION_COOKIE_NAME, AuthService
from app.services.file_manager import FileManagerService
from app.services.log_buffer import LogBuffer
from app.services.map_integration import BlueMapIntegrationService
from app.services.minecraft_manager import MinecraftServerManager
from app.services.panel_settings import PanelSettingsService
from app.services.server_properties import ServerPropertiesService
from app.services.server_instances import ServerInstanceService
from app.services.telegram_bot import TelegramBotService


def get_settings_from_request(request: Request) -> AppSettings:
    return cast(AppSettings, request.app.state.settings)


def get_instance_service(request: Request) -> ServerInstanceService:
    return cast(ServerInstanceService, request.app.state.instance_service)


def get_log_buffer(request: Request) -> LogBuffer:
    return cast(LogBuffer, request.app.state.log_buffer)


def get_manager(request: Request) -> MinecraftServerManager:
    return cast(MinecraftServerManager, request.app.state.minecraft_manager)


def get_map_service(request: Request) -> BlueMapIntegrationService:
    return cast(BlueMapIntegrationService, request.app.state.map_service)


def get_properties_service(request: Request) -> ServerPropertiesService:
    return cast(ServerPropertiesService, request.app.state.properties_service)


def get_file_manager(request: Request) -> FileManagerService:
    return cast(FileManagerService, request.app.state.file_manager)


def get_panel_settings_service(request: Request) -> PanelSettingsService:
    return cast(PanelSettingsService, request.app.state.panel_settings_service)


def get_auth_service(request: Request) -> AuthService:
    return cast(AuthService, request.app.state.auth_service)


def get_telegram_bot_service(request: Request) -> TelegramBotService:
    return cast(TelegramBotService, request.app.state.telegram_bot_service)


def get_current_user(request: Request) -> AuthUser:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_auth_service(request).get_user_by_session_token(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    return user


def require_permission(permission: str):
    def dependency(request: Request) -> AuthUser:
        user = get_current_user(request)
        if not user.has_permission(permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission_denied")
        return user

    return dependency


def require_admin(request: Request) -> AuthUser:
    user = get_current_user(request)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission_denied")
    return user
