from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_auth_service, get_current_user, require_admin
from app.models.auth import (
    AuthResponse,
    AuthUser,
    InviteLinkResponse,
    InviteLoginRequest,
    LoginRequest,
)
from app.services.auth import SESSION_COOKIE_NAME

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _set_session_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: Request, response: Response, payload: LoginRequest) -> AuthResponse:
    try:
        token, user = get_auth_service(request).login_admin(payload.username, payload.password)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _set_session_cookie(response, token, get_auth_service(request).session_max_age)
    return AuthResponse(user=user)


@router.post("/invite-login", response_model=AuthResponse)
async def invite_login(
    request: Request,
    response: Response,
    payload: InviteLoginRequest,
) -> AuthResponse:
    try:
        token, user = get_auth_service(request).login_invite(payload.token)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _set_session_cookie(response, token, get_auth_service(request).session_max_age)
    return AuthResponse(user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    get_auth_service(request).logout(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.get("/me", response_model=AuthResponse)
async def me(current_user: AuthUser = Depends(get_current_user)) -> AuthResponse:
    return AuthResponse(user=current_user)


@router.get("/invite", response_model=InviteLinkResponse)
async def get_invite(
    request: Request,
    current_user: AuthUser = Depends(require_admin),
) -> dict:
    return get_auth_service(request).invite_status(_base_url(request))


@router.post("/invite", response_model=InviteLinkResponse)
async def create_invite(
    request: Request,
    current_user: AuthUser = Depends(require_admin),
) -> dict:
    return get_auth_service(request).create_invite(_base_url(request))


@router.delete("/invite", response_model=InviteLinkResponse)
async def revoke_invite(
    request: Request,
    current_user: AuthUser = Depends(require_admin),
) -> dict:
    return get_auth_service(request).revoke_invite(_base_url(request))
