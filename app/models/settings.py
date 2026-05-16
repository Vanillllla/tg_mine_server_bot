from pydantic import BaseModel, Field


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


class PublicLink(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    icon_path: str = Field(min_length=1, max_length=500)


class PublicLinks(BaseModel):
    discord: PublicLink


class PublicPanelSettings(BaseModel):
    links: PublicLinks
