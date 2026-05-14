from typing import Any

from pydantic import BaseModel, Field


class ServerPropertiesResponse(BaseModel):
    exists: bool
    raw: str
    values: dict[str, str] = Field(default_factory=dict)


class UpdateServerPropertiesRequest(BaseModel):
    values: dict[str, Any] | None = None
    raw: str | None = None
