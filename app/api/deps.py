from typing import cast

from fastapi import Request

from app.core.settings import AppSettings
from app.services.log_buffer import LogBuffer
from app.services.minecraft_manager import MinecraftServerManager
from app.services.server_instances import ServerInstanceService


def get_settings_from_request(request: Request) -> AppSettings:
    return cast(AppSettings, request.app.state.settings)


def get_instance_service(request: Request) -> ServerInstanceService:
    return cast(ServerInstanceService, request.app.state.instance_service)


def get_log_buffer(request: Request) -> LogBuffer:
    return cast(LogBuffer, request.app.state.log_buffer)


def get_manager(request: Request) -> MinecraftServerManager:
    return cast(MinecraftServerManager, request.app.state.minecraft_manager)

