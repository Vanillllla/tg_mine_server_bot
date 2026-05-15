from datetime import datetime

from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    id: str
    username: str
    role: str
    permissions: list[str] = Field(default_factory=list)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class AdminPasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class InviteLoginRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class AuthResponse(BaseModel):
    user: AuthUser


class InviteLinkResponse(BaseModel):
    active: bool
    token: str | None = None
    url: str | None = None
    created_at: datetime | None = None
    revoked_at: datetime | None = None
