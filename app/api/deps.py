from typing import cast

from fastapi import Request

from app.core.settings import AppSettings
from app.services.file_manager import FileManagerService
from app.services.log_buffer import LogBuffer
from app.services.minecraft_manager import MinecraftServerManager
from app.services.panel_settings import PanelSettingsService
from app.services.server_properties import ServerPropertiesService
from app.services.server_instances import ServerInstanceService


def get_settings_from_request(request: Request) -> AppSettings:
    return cast(AppSettings, request.app.state.settings)


def get_instance_service(request: Request) -> ServerInstanceService:
    return cast(ServerInstanceService, request.app.state.instance_service)


def get_log_buffer(request: Request) -> LogBuffer:
    return cast(LogBuffer, request.app.state.log_buffer)


def get_manager(request: Request) -> MinecraftServerManager:
    return cast(MinecraftServerManager, request.app.state.minecraft_manager)


def get_properties_service(request: Request) -> ServerPropertiesService:
    return cast(ServerPropertiesService, request.app.state.properties_service)


def get_file_manager(request: Request) -> FileManagerService:
    return cast(FileManagerService, request.app.state.file_manager)


def get_panel_settings_service(request: Request) -> PanelSettingsService:
    return cast(PanelSettingsService, request.app.state.panel_settings_service)
