import json
import os
import shlex
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_manager, require_admin
from app.models.auth import AuthUser

router = APIRouter(prefix="/api/updater", tags=["updater"])

GITHUB_REPO = os.getenv("MC_PANEL_GITHUB_REPO", "Vanillllla/mc-server-controller")
CURRENT_VERSION_FALLBACK = os.getenv("MC_PANEL_VERSION", "0.1.1")
UPDATE_COMMAND = os.getenv(
    "MC_PANEL_UPDATE_COMMAND",
    "/usr/bin/sudo /usr/local/sbin/mc-panel-update-dispatch",
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
VERSION_FILE = PROJECT_ROOT / "VERSION"


def _current_version() -> str:
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        version = ""
    return version or CURRENT_VERSION_FALLBACK


def _normalize_version(version: str) -> str:
    return version.strip().lstrip("v")


def _update_command_args(version: str) -> list[str]:
    args = shlex.split(UPDATE_COMMAND)
    if not args:
        raise HTTPException(status_code=500, detail="update_command_is_empty")
    return [*args, version]


def _github_latest_release() -> dict[str, Any]:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "mc-server-controller-updater",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise HTTPException(status_code=404, detail="github_release_not_found") from exc
        raise HTTPException(status_code=502, detail=f"github_api_error_{exc.code}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"github_api_unavailable: {exc}") from exc


def _latest_payload() -> dict[str, Any]:
    release = _github_latest_release()
    latest_version = str(release.get("tag_name") or "").strip()
    if not latest_version:
        raise HTTPException(status_code=502, detail="github_release_without_tag")
    current_version = _current_version()
    return {
        "repository": GITHUB_REPO,
        "current_version": current_version,
        "latest_version": latest_version,
        "update_available": _normalize_version(latest_version) != _normalize_version(current_version),
        "release_name": release.get("name") or latest_version,
        "html_url": release.get("html_url") or "",
        "published_at": release.get("published_at"),
        "body": release.get("body") or "",
    }


@router.get("/check")
async def check_for_updates(
    current_user: AuthUser = Depends(require_admin),
) -> dict[str, Any]:
    return _latest_payload()


@router.post("/apply", status_code=status.HTTP_202_ACCEPTED)
async def apply_update(
    request: Request,
    current_user: AuthUser = Depends(require_admin),
) -> dict[str, Any]:
    latest = _latest_payload()
    if not latest["update_available"]:
        return {"accepted": False, "reason": "already_up_to_date", **latest}

    manager = get_manager(request)
    if manager.is_running():
        raise HTTPException(status_code=409, detail="minecraft_server_must_be_stopped_before_update")

    try:
        subprocess.Popen(
            _update_command_args(latest["latest_version"]),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"update_start_failed: {exc}") from exc

    return {"accepted": True, **latest}
