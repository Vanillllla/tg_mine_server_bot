from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.server import validate_server_id


ModSourceType = Literal["modrinth", "url", "local"]


class ModCatalogItem(BaseModel):
    id: str
    display_name: str
    source_type: ModSourceType = "modrinth"
    source: str = ""
    server_types: list[str] = Field(default_factory=list)
    minecraft_versions: list[str] = Field(default_factory=list)
    enabled: bool = True
    file_name: str = ""
    cached_path: str = ""
    version: str = ""
    last_error: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_server_id(value)


class ModCatalogItemRequest(BaseModel):
    id: str
    display_name: str
    source_type: ModSourceType = "modrinth"
    source: str = ""
    server_types: list[str] = Field(default_factory=list)
    minecraft_versions: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_server_id(value)


class ModApplyResponse(BaseModel):
    installed: list[ModCatalogItem] = Field(default_factory=list)
    skipped: list[ModCatalogItem] = Field(default_factory=list)
