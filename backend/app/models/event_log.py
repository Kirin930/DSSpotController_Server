from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base_class import Base
from ..utils.time import utc_now


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    node_id: Mapped[str | None] = mapped_column(String(64), index=True)
    spot_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_type: Mapped[str | None] = mapped_column(String(32))
    actor_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
