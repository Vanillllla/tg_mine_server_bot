from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["web"])

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@router.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@router.get("/invite/{token}", include_in_schema=False)
async def invite_entry(token: str) -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
