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
