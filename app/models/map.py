from pydantic import BaseModel, Field

from app.models.server import ServerMapSettings


class MinecraftVersion(BaseModel):
    id: str
    type: str = "release"
    release_time: str = ""


class MapProvider(BaseModel):
    id: str
    display_name: str
    description: str
    supported_server_types: list[str] = Field(default_factory=list)


class MapInstallRequest(BaseModel):
    provider: str = "bluemap"


class MapProviderVersion(BaseModel):
    version_number: str
    file_name: str
    download_url: str
    loaders: list[str] = Field(default_factory=list)
    game_versions: list[str] = Field(default_factory=list)


class MapStatusResponse(BaseModel):
    configured: bool
    installed: bool
    status: str
    provider: str = "bluemap"
    map: ServerMapSettings
    map_url: str | None = None
    message: str = ""

