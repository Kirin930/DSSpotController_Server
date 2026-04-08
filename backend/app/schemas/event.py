from __future__ import annotations

from datetime import datetime

from .common import ApiModel


class EventResponse(ApiModel):
    id: str
    event_type: str
    node_id: str | None = None
    spot_id: str | None = None
    details: str
    created_at: datetime
