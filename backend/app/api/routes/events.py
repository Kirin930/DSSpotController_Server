from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..deps import get_current_admin, get_db, get_event_service
from ...models.admin_user import AdminUser
from ...schemas.event import EventResponse
from ...services.event_service import EventService


router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventResponse])
def list_events(
    limit: int = Query(default=50, ge=1, le=500),
    node_id: str | None = Query(default=None, alias="nodeId"),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
    event_service: EventService = Depends(get_event_service),
) -> list[EventResponse]:
    return [
        EventResponse.model_validate(event)
        for event in event_service.list_events(db, limit=limit, node_id=node_id)
    ]
