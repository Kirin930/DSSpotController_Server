from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import (
    get_current_admin,
    get_db,
    get_scheduler_service,
    require_current_admin_write,
)
from ...models.admin_user import AdminUser
from ...schemas.scheduler import (
    SchedulerActionResponse,
    SchedulerConfigResponse,
    SchedulerConfigUpdate,
)
from ...services.scheduler_service import SchedulerService


router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("", response_model=SchedulerConfigResponse)
def get_scheduler_config(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
) -> SchedulerConfigResponse:
    return scheduler_service.to_response(scheduler_service.get_config(db))


@router.put("", response_model=SchedulerConfigResponse)
async def update_scheduler_config(
    payload: SchedulerConfigUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
) -> SchedulerConfigResponse:
    config = await scheduler_service.update_config(
        db, payload, actor_id=current_admin.username
    )
    return scheduler_service.to_response(config)


@router.post("/start", response_model=SchedulerActionResponse)
async def start_scheduler(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
) -> SchedulerActionResponse:
    await scheduler_service.start_autoplay(db, actor_id=current_admin.username)
    return SchedulerActionResponse(message="Autoplay started")


@router.post("/stop", response_model=SchedulerActionResponse)
async def stop_scheduler(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
) -> SchedulerActionResponse:
    await scheduler_service.stop_autoplay(db, actor_id=current_admin.username)
    return SchedulerActionResponse(message="Autoplay stopped")
