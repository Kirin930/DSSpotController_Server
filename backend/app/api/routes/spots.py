from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..deps import (
    get_auth_service,
    get_current_admin,
    get_db,
    get_spot_service,
    require_current_admin_write,
)
from ...models.admin_user import AdminUser
from ...schemas.spot import SpotResponse, SpotUpdateRequest
from ...services.auth_service import AuthService
from ...services.spot_service import SpotService


router = APIRouter(prefix="/spots", tags=["spots"])


@router.get("", response_model=list[SpotResponse])
def list_spots(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
    spot_service: SpotService = Depends(get_spot_service),
) -> list[SpotResponse]:
    return [SpotResponse.model_validate(spot) for spot in spot_service.list_spots(db)]


@router.post("", response_model=SpotResponse)
async def create_spot(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    spot_service: SpotService = Depends(get_spot_service),
) -> SpotResponse:
    content = await file.read()
    spot = spot_service.create_spot(
        db,
        title=title,
        content=content,
        original_filename=file.filename or "spot.bin",
        content_type=file.content_type,
        actor_id=current_admin.username,
    )
    return SpotResponse.model_validate(spot)


@router.get("/{spot_id}", response_model=SpotResponse)
def get_spot(
    spot_id: str,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
    spot_service: SpotService = Depends(get_spot_service),
) -> SpotResponse:
    return SpotResponse.model_validate(spot_service.get_spot(db, spot_id))


@router.patch("/{spot_id}", response_model=SpotResponse)
def update_spot(
    spot_id: str,
    payload: SpotUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    spot_service: SpotService = Depends(get_spot_service),
) -> SpotResponse:
    spot = spot_service.update_spot(
        db, spot_id, payload, actor_id=current_admin.username
    )
    return SpotResponse.model_validate(spot)


@router.get("/{spot_id}/download")
def download_spot(
    spot_id: str,
    request: Request,
    node_id: str | None = Query(default=None, alias="nodeId"),
    expires: int | None = Query(default=None),
    signature: str | None = Query(default=None),
    db: Session = Depends(get_db),
    spot_service: SpotService = Depends(get_spot_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    current_admin = auth_service.get_current_admin(db, request)
    if current_admin is not None:
        spot = spot_service.get_spot(db, spot_id)
    else:
        if node_id is None or expires is None or signature is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signed node download parameters are required",
            )
        spot = spot_service.verify_download_access(
            db,
            spot_id=spot_id,
            node_id=node_id,
            expires=expires,
            signature=signature,
        )
    return FileResponse(
        path=spot.storage_path,
        filename=spot.filename,
        media_type=spot.mime_type,
    )
