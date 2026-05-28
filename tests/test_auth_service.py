from pathlib import Path

from app.core.settings import AppSettings
from app.services.auth import AuthService


def make_service(tmp_path: Path) -> AuthService:
    settings = AppSettings(panel_home=tmp_path / "mc-panel")
    settings.ensure_runtime_layout()
    return AuthService(settings)


def test_admin_login_creates_session(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    token, user = service.login_admin("admin", "change-me")

    assert token
    assert user.role == "admin"
    assert user.has_permission("files.view")
    assert service.get_user_by_session_token(token).id == "admin"


def test_invite_login_uses_limited_permissions(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    invite = service.create_invite("http://testserver")

    token, user = service.login_invite(invite["token"])

    assert token
    assert user.role == "user"
    assert user.has_permission("server.start")
    assert user.has_permission("map.view")
    assert not user.has_permission("files.view")
    assert not user.has_permission("map.manage")
    assert not user.has_permission("console.view")


def test_revoked_invite_invalidates_existing_sessions(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    invite = service.create_invite("http://testserver")
    token, _ = service.login_invite(invite["token"])

    service.revoke_invite("http://testserver")

    assert service.get_user_by_session_token(token) is None


def test_recreated_invite_invalidates_existing_sessions(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    invite = service.create_invite("http://testserver")
    token, _ = service.login_invite(invite["token"])

    service.create_invite("http://testserver")

    assert service.get_user_by_session_token(token) is None


def test_invite_token_helpers_follow_active_invite(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    invite = service.create_invite("http://testserver")

    assert service.invite_token_is_active(invite["token"]) is True
    assert service.invite_token_is_active("bad-token") is False
    assert service.active_invite_token_hash()

    service.revoke_invite("http://testserver")

    assert service.invite_token_is_active(invite["token"]) is False
    assert service.active_invite_token_hash() == ""


def test_revoked_invite_rejects_login(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    invite = service.create_invite("http://testserver")
    service.revoke_invite("http://testserver")

    try:
        service.login_invite(invite["token"])
    except PermissionError as exc:
        assert str(exc) == "invite_is_closed"
    else:
        raise AssertionError("revoked invite was accepted")


def test_admin_password_change_updates_login(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    service.change_admin_password("change-me", "new-password")

    try:
        service.login_admin("admin", "change-me")
    except PermissionError as exc:
        assert str(exc) == "invalid_credentials"
    else:
        raise AssertionError("old admin password was accepted")

    token, user = service.login_admin("admin", "new-password")

    assert token
    assert user.role == "admin"
