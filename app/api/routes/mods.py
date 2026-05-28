from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import ValidationError

from app.api.deps import get_instance_service, get_mod_catalog_service, require_permission
from app.models.auth import AuthUser
from app.models.mod_catalog import ModCatalogItem, ModCatalogItemRequest


router = APIRouter(prefix="/api/mods", tags=["mods"])


def _request_from_form(
    id: str,
    display_name: str,
    source_type: str,
    source: str,
    server_types: str,
    minecraft_versions: str,
    enabled: bool,
) -> ModCatalogItemRequest:
    try:
        return ModCatalogItemRequest(
            id=id.strip().lower(),
            display_name=display_name.strip(),
            source_type=source_type,
            source=source.strip(),
            server_types=_split_list(server_types),
            minecraft_versions=_split_list(minecraft_versions),
            enabled=enabled,
        )
    except ValidationError as exc:
        first = exc.errors()[0] if exc.errors() else {}
        raise ValueError(str(first.get("msg") or exc)) from exc


def _split_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.replace("\n", ",").split(",") if item.strip()]


@router.get("", response_model=list[ModCatalogItem])
async def list_mods(
    request: Request,
    current_user: AuthUser = Depends(require_permission("files.manage_mods")),
) -> list[ModCatalogItem]:
    return get_mod_catalog_service(request).list_items()


@router.post("", response_model=ModCatalogItem, status_code=status.HTTP_201_CREATED)
async def add_remote_mod(
    request: Request,
    payload: ModCatalogItemRequest,
    current_user: AuthUser = Depends(require_permission("files.manage_mods")),
) -> ModCatalogItem:
    try:
        return get_mod_catalog_service(request).add_remote_item(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload", response_model=ModCatalogItem, status_code=status.HTTP_201_CREATED)
async def upload_mod(
    request: Request,
    id: str = Form(...),
    display_name: str = Form(...),
    source: str = Form(""),
    server_types: str = Form(""),
    minecraft_versions: str = Form(""),
    enabled: bool = Form(True),
    mod_file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_permission("files.manage_mods")),
) -> ModCatalogItem:
    if not mod_file.filename:
        raise HTTPException(status_code=400, detail="mod_file_required")
    try:
        payload = _request_from_form(
            id=id,
            display_name=display_name,
            source_type="local",
            source=source,
            server_types=server_types,
            minecraft_versions=minecraft_versions,
            enabled=enabled,
        )
        return get_mod_catalog_service(request).add_uploaded_item(
            payload,
            mod_file.filename,
            mod_file.file,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{mod_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mod(
    request: Request,
    mod_id: str,
    delete_cached_file: bool = False,
    current_user: AuthUser = Depends(require_permission("files.manage_mods")),
) -> None:
    try:
        get_mod_catalog_service(request).delete_item(mod_id, delete_cached_file=delete_cached_file)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="mod_not_found") from exc


@router.post("/apply/{server_id}", response_model=list[ModCatalogItem])
async def apply_mods_to_server(
    request: Request,
    server_id: str,
    current_user: AuthUser = Depends(require_permission("files.manage_mods")),
) -> list[ModCatalogItem]:
    try:
        server = get_instance_service(request).get_server(server_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="server_not_found") from exc
    return get_mod_catalog_service(request).auto_install_for_server(server)
