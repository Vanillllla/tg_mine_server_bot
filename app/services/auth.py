import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.json_store import read_json, write_json_atomic
from app.core.settings import AppSettings
from app.models.auth import AuthUser


SESSION_COOKIE_NAME = "mc_panel_session"

PERMISSIONS = {
    "servers.view",
    "servers.create",
    "servers.import",
    "servers.activate",
    "servers.delete",
    "servers.edit_launch_settings",
    "server.start",
    "server.stop",
    "server.restart",
    "server.kill",
    "server.view_status",
    "server.view_metrics",
    "console.view",
    "console.send_command",
    "console.send_dangerous_command",
    "client_mods.download",
    "files.view",
    "files.upload",
    "files.download",
    "files.edit",
    "files.delete",
    "files.rename",
    "files.manage_world",
    "files.manage_mods",
    "files.upload_core",
    "properties.view",
    "properties.quick_edit",
    "properties.raw_edit",
    "rcon.view",
    "rcon.manage",
    "rcon.regenerate_password",
    "telegram.view",
    "telegram.start",
    "telegram.stop",
    "telegram.edit_token",
    "users.view",
    "users.manage",
    "roles.manage",
    "localization.view",
    "localization.edit",
    "audit.view",
}

ADMIN_PERMISSIONS = sorted(PERMISSIONS)
INVITED_USER_PERMISSIONS = sorted(
    {
        "server.start",
        "server.view_status",
        "server.view_metrics",
        "client_mods.download",
    }
)


class AuthService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.admin_username = os.getenv("MC_PANEL_ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("MC_PANEL_ADMIN_PASSWORD", "change-me")
        self.session_ttl_seconds = max(
            600,
            int(os.getenv("MC_PANEL_SESSION_TTL_SECONDS", str(7 * 24 * 60 * 60))),
        )

    @property
    def session_max_age(self) -> int:
        return self.session_ttl_seconds

    def login_admin(self, username: str, password: str) -> tuple[str, AuthUser]:
        if not self._safe_equals(username, self.admin_username) or not self._safe_equals(
            password,
            self.admin_password,
        ):
            raise PermissionError("invalid_credentials")
        return self._create_session(user_id="admin", username=self.admin_username, role="admin")

    def login_invite(self, token: str) -> tuple[str, AuthUser]:
        auth = self._read_auth()
        invite = auth.setdefault("invite", {})
        active_token = str(invite.get("token", "") or "")
        if not active_token or invite.get("revoked_at"):
            raise PermissionError("invite_is_closed")
        if not self._safe_equals(token, active_token):
            raise PermissionError("invalid_invite")
        user_id = f"invite:{self._token_hash(active_token)[:12]}"
        return self._create_session(user_id=user_id, username="invited-user", role="user")

    def get_user_by_session_token(self, token: str | None) -> AuthUser | None:
        if not token:
            return None
        auth = self._read_auth()
        sessions = auth.setdefault("sessions", {})
        session_hash = self._token_hash(token)
        session = sessions.get(session_hash)
        if not session:
            return None

        expires_at = self._parse_datetime(session.get("expires_at"))
        if expires_at is not None and expires_at <= self._now():
            del sessions[session_hash]
            self._write_auth(auth)
            return None

        return self._user_for_role(
            user_id=str(session.get("user_id", "")),
            username=str(session.get("username", "")),
            role=str(session.get("role", "")),
        )

    def logout(self, token: str | None) -> None:
        if not token:
            return
        auth = self._read_auth()
        sessions = auth.setdefault("sessions", {})
        session_hash = self._token_hash(token)
        if session_hash in sessions:
            del sessions[session_hash]
            self._write_auth(auth)

    def invite_status(self, base_url: str) -> dict[str, Any]:
        invite = self._read_auth().setdefault("invite", {})
        return self._invite_payload(invite, base_url)

    def create_invite(self, base_url: str) -> dict[str, Any]:
        auth = self._read_auth()
        token = secrets.token_urlsafe(32)
        invite = {
            "token": token,
            "created_at": self._now().isoformat(),
            "revoked_at": None,
        }
        auth["invite"] = invite
        self._write_auth(auth)
        return self._invite_payload(invite, base_url)

    def revoke_invite(self, base_url: str) -> dict[str, Any]:
        auth = self._read_auth()
        invite = auth.setdefault("invite", {})
        if invite.get("token") and not invite.get("revoked_at"):
            invite["revoked_at"] = self._now().isoformat()
        invite["token"] = ""
        self._write_auth(auth)
        return self._invite_payload(invite, base_url)

    def _create_session(self, user_id: str, username: str, role: str) -> tuple[str, AuthUser]:
        auth = self._read_auth()
        sessions = auth.setdefault("sessions", {})
        self._cleanup_expired_sessions(sessions)

        token = secrets.token_urlsafe(32)
        now = self._now()
        sessions[self._token_hash(token)] = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self.session_ttl_seconds)).isoformat(),
        }
        self._write_auth(auth)
        return token, self._user_for_role(user_id=user_id, username=username, role=role)

    def _user_for_role(self, user_id: str, username: str, role: str) -> AuthUser:
        if role == "admin":
            return AuthUser(
                id=user_id or "admin",
                username=username or self.admin_username,
                role="admin",
                permissions=ADMIN_PERMISSIONS,
            )
        return AuthUser(
            id=user_id or "invite",
            username=username or "invited-user",
            role="user",
            permissions=INVITED_USER_PERMISSIONS,
        )

    def _read_auth(self) -> dict[str, Any]:
        auth = read_json(self.settings.auth_config_path, default={})
        auth.setdefault("invite", {})
        auth.setdefault("sessions", {})
        return auth

    def _write_auth(self, auth: dict[str, Any]) -> None:
        write_json_atomic(self.settings.auth_config_path, auth)

    def _cleanup_expired_sessions(self, sessions: dict[str, Any]) -> None:
        now = self._now()
        expired = [
            token_hash
            for token_hash, session in sessions.items()
            if (self._parse_datetime(session.get("expires_at")) or now) <= now
        ]
        for token_hash in expired:
            del sessions[token_hash]

    def _invite_payload(self, invite: dict[str, Any], base_url: str) -> dict[str, Any]:
        token = str(invite.get("token", "") or "")
        active = bool(token and not invite.get("revoked_at"))
        root = base_url.rstrip("/")
        return {
            "active": active,
            "token": token if active else None,
            "url": f"{root}/invite/{token}" if active else None,
            "created_at": self._parse_datetime(invite.get("created_at")),
            "revoked_at": self._parse_datetime(invite.get("revoked_at")),
        }

    @staticmethod
    def _safe_equals(left: str, right: str) -> bool:
        return hmac.compare_digest(str(left), str(right))

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
