from fastapi import APIRouter, HTTPException, Request

from app.api.deps import get_map_service

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/minecraft-versions")
async def list_minecraft_versions(request: Request) -> dict:
    try:
        versions = get_map_service(request).list_minecraft_versions()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"minecraft_versions_unavailable: {exc}") from exc
    return {"items": versions}

