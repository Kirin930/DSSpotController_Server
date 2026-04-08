from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..models.event_log import EventLog
from ..models.spot import Spot
from ..utils.time import utc_now


@dataclass(slots=True)
class RetentionSweepResult:
    deleted_event_count: int = 0
    deleted_spot_count: int = 0


class RetentionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def sweep(self, db: Session) -> RetentionSweepResult:
        result = RetentionSweepResult()
        event_cutoff = utc_now() - timedelta(days=self.settings.event_retention_days)
        inactive_spot_cutoff = utc_now() - timedelta(
            days=self.settings.inactive_spot_retention_days
        )

        old_inactive_spots = list(
            db.scalars(
                select(Spot).where(
                    Spot.active.is_(False),
                    Spot.updated_at < inactive_spot_cutoff,
                )
            )
        )
        for spot in old_inactive_spots:
            storage_path = Path(spot.storage_path)
            if storage_path.exists():
                storage_path.unlink()
            db.delete(spot)
            result.deleted_spot_count += 1

        delete_result = db.execute(
            delete(EventLog).where(EventLog.created_at < event_cutoff)
        )
        result.deleted_event_count = int(delete_result.rowcount or 0)
        if result.deleted_event_count or result.deleted_spot_count:
            db.commit()
        return result
