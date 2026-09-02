import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


SERVER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def validate_server_id(value: str) -> str:
    if not SERVER_ID_RE.match(value):
        raise ValueError("server_id_must_be_slug")
    return value


class ServerStatus(str, Enum):
    OFF = "OFF"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class LaunchMode(str, Enum):
    JAR = "jar"
    FORGE_ARGS = "forge_args"


class ServerMapSettings(BaseModel):
    enabled: bool = False
    provider: str = "bluemap"
    installed: bool = False
    needs_restart: bool = False
    web_port: int | None = None
    bind_host: str = "127.0.0.1"
    provider_version: str = ""
    jar_path: str = ""
    last_error: str = ""


class ServerInstance(BaseModel):
    id: str
    display_name: str
    server_dir: str
    jar_file: str
    launch_mode: LaunchMode = LaunchMode.JAR
    minecraft_version: str = ""
    server_type: str = "custom"
    java_path: str = "java"
    xms_mb: int = 256
    xmx_mb: int = 1024
    jvm_args: list[str] = Field(default_factory=lambda: ["-Dfile.encoding=UTF-8"])
    server_args: list[str] = Field(default_factory=lambda: ["nogui"])
    eula_accept: bool = False
    auto_restart: bool = False
    startup_timeout: int = 180
    map: ServerMapSettings = Field(default_factory=ServerMapSettings)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_server_id(value)

    @field_validator("xms_mb", "xmx_mb")
    @classmethod
    def validate_memory(cls, value: int) -> int:
        if value < 64:
            raise ValueError("memory_must_be_at_least_64_mb")
        return value

    @field_validator("startup_timeout")
    @classmethod
    def validate_startup_timeout(cls, value: int) -> int:
        if value < 5:
            raise ValueError("startup_timeout_too_low")
        return value

    @model_validator(mode="after")
    def validate_memory_order(self) -> "ServerInstance":
        if self.xmx_mb < self.xms_mb:
            raise ValueError("xmx_mb_must_be_greater_or_equal_to_xms_mb")
        return self

    @property
    def jar_path(self) -> Path:
        return Path(self.server_dir) / self.jar_file


class CreateServerInstanceRequest(BaseModel):
    id: str
    display_name: str
    server_dir: str | None = None
    jar_file: str
    launch_mode: LaunchMode = LaunchMode.JAR
    minecraft_version: str = ""
    server_type: str = "custom"
    java_path: str = "java"
    xms_mb: int = 1024
    xmx_mb: int = 1024
    jvm_args: list[str] = Field(default_factory=lambda: ["-Dfile.encoding=UTF-8"])
    server_args: list[str] = Field(default_factory=lambda: ["nogui"])
    eula_accept: bool = False
    auto_restart: bool = False
    startup_timeout: int = 180

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_server_id(value)


class UpdateServerInstanceRequest(BaseModel):
    display_name: str | None = None
    jar_file: str | None = None
    launch_mode: LaunchMode | None = None
    minecraft_version: str | None = None
    server_type: str | None = None
    java_path: str | None = None
    xms_mb: int | None = None
    xmx_mb: int | None = None
    jvm_args: list[str] | None = None
    server_args: list[str] | None = None
    eula_accept: bool | None = None
    auto_restart: bool | None = None
    startup_timeout: int | None = None
    map: ServerMapSettings | None = None


class SelectActiveServerJarRequest(BaseModel):
    path: str = Field(min_length=1, max_length=512)


class SelectActiveLaunchTargetRequest(BaseModel):
    path: str = Field(min_length=1, max_length=512)
    launch_mode: LaunchMode = LaunchMode.JAR


class ConsoleCommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=4096)


class ServerStatusResponse(BaseModel):
    status: ServerStatus
    active_server_id: str | None = None
    pid: int | None = None
    uptime_seconds: float | None = None
    start_error: str = ""
    exit_code: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ServerDiskUsage(BaseModel):
    id: str
    size_bytes: int = Field(ge=0)


class ServerStorageSummary(BaseModel):
    total_bytes: int = Field(ge=0)
    used_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)
    used_percent: float = Field(ge=0, le=100)
    servers_bytes: int = Field(ge=0)
    servers: list[ServerDiskUsage] = Field(default_factory=list)
