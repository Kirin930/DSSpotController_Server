from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.event_log import EventLog


class EventService:
    def log(
        self,
        db: Session,
        event_type: str,
        *,
        details: str = "",
        node_id: str | None = None,
        spot_id: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
    ) -> EventLog:
        event = EventLog(
            event_type=event_type,
            node_id=node_id,
            spot_id=spot_id,
            actor_type=actor_type,
            actor_id=actor_id,
            details=details,
        )
        db.add(event)
        return event

    def list_events(
        self, db: Session, *, limit: int = 50, node_id: str | None = None
    ) -> list[EventLog]:
        query = select(EventLog).order_by(EventLog.created_at.desc()).limit(limit)
        if node_id:
            query = query.where(EventLog.node_id == node_id)
        return list(db.scalars(query))
