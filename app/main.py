from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import console_ws, health, servers
from app.core.settings import get_settings
from app.services.log_buffer import LogBuffer
from app.services.minecraft_manager import MinecraftServerManager
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
    yield
    await manager.shutdown()


app = FastAPI(
    title="Minecraft Web Panel API",
    version="0.1.0",
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
app.include_router(servers.router)
app.include_router(console_ws.router)

