from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from conftest import login, upload_spot

from app.models.event_log import EventLog
from app.models.spot import Spot
from app.utils.time import utc_now


def test_retention_sweep_removes_old_events_and_inactive_spots(client):
    login(client)
    spot = upload_spot(client)

    with client.app.state.session_factory() as db:
        db.add(
            EventLog(
                event_type="OLD_EVENT",
                details="old event",
                created_at=utc_now()
                - timedelta(days=client.app.state.settings.event_retention_days + 1),
            )
        )
        stored_spot = db.get(Spot, spot["id"])
        stored_spot.active = False
        stored_spot.updated_at = utc_now() - timedelta(
            days=client.app.state.settings.inactive_spot_retention_days + 1
        )
        storage_path = stored_spot.storage_path
        db.commit()

    with client.app.state.session_factory() as db:
        result = client.app.state.retention_service.sweep(db)

    assert result.deleted_event_count == 1
    assert result.deleted_spot_count == 1
    assert not Path(storage_path).exists()
