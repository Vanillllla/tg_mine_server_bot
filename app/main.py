from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, client_mods, console_ws, files, health, properties, servers, settings, web
from app.core.settings import get_settings
from app.services.file_manager import FileManagerService
from app.services.auth import AuthService
from app.services.log_buffer import LogBuffer
from app.services.minecraft_manager import MinecraftServerManager
from app.services.panel_settings import PanelSettingsService
from app.services.server_properties import ServerPropertiesService
from app.services.server_instances import ServerInstanceService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_runtime_layout()

    instance_service = ServerInstanceService(settings)
    log_buffer = LogBuffer(max_lines=settings.log_buffer_lines)
    manager = MinecraftServerManager(instance_service=instance_service, log_buffer=log_buffer)

    app.state.settings = settings
    app.state.instance_service = instance_service
    app.state.log_buffer = log_buffer
    app.state.minecraft_manager = manager
    app.state.properties_service = ServerPropertiesService()
    app.state.file_manager = FileManagerService()
    app.state.panel_settings_service = PanelSettingsService(settings)
    app.state.auth_service = AuthService(settings)
    yield
    await manager.shutdown()


app = FastAPI(
    title="Minecraft Web Panel API",
    version="0.1.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(properties.router)
app.include_router(files.router)
app.include_router(client_mods.router)
app.include_router(settings.router)
app.include_router(console_ws.router)
app.include_router(web.router)
app.mount(
    "/assets",
    StaticFiles(directory=Path(__file__).resolve().parent / "web" / "assets"),
    name="assets",
)
