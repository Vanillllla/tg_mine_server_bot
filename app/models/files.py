from pydantic import BaseModel, Field


class WriteTextFileRequest(BaseModel):
    content: str = Field(max_length=2_000_000)


class CreateDirectoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class RenamePathRequest(BaseModel):
    new_name: str = Field(min_length=1, max_length=255)
