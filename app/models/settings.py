import re

from pydantic import BaseModel, Field, field_validator, model_validator


TELEGRAM_BOT_TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")


class JavaRuntime(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=500)
    is_default: bool = False


class UpsertJavaRuntimeRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=500)
    is_default: bool = False


class SetDefaultJavaRuntimeRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64)


class EmptyShutdownSettings(BaseModel):
    enabled: bool = False
    shutdown_if_empty_minutes: int = Field(default=5, ge=1, le=1440)


class TelegramSettings(BaseModel):
    autostart: bool = False
    bot_token: str = Field(default="", max_length=200)
    admin_ids: list[int] = Field(default_factory=list, max_length=50)

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, value: str) -> str:
        value = value.strip()
        if value and not TELEGRAM_BOT_TOKEN_RE.match(value):
            raise ValueError("telegram_bot_token_invalid")
        return value

    @field_validator("admin_ids")
    @classmethod
    def validate_admin_ids(cls, value: list[int]) -> list[int]:
        seen: set[int] = set()
        normalized: list[int] = []
        for admin_id in value:
            if admin_id <= 0:
                raise ValueError("telegram_admin_id_must_be_positive")
            if admin_id not in seen:
                seen.add(admin_id)
                normalized.append(admin_id)
        return normalized

    @model_validator(mode="after")
    def validate_autostart_token(self) -> "TelegramSettings":
        if self.autostart and not self.bot_token:
            raise ValueError("telegram_bot_token_required")
        return self


class TelegramSettingsResponse(TelegramSettings):
    running: bool = False
    last_error: str = ""


class PublicLink(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    icon_path: str = Field(min_length=1, max_length=500)


class PublicLinks(BaseModel):
    discord: PublicLink


class PublicPanelSettings(BaseModel):
    links: PublicLinks
