from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base_class import Base
from ..utils.enums import NodeConnectionState, NodeOperationalState
from ..utils.time import utc_now


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    auth_token_hash: Mapped[str] = mapped_column(String(512))
    platform: Mapped[str] = mapped_column(String(32), default="android")
    app_version: Mapped[str | None] = mapped_column(String(32))
    device_model: Mapped[str | None] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    autoplay_selected: Mapped[bool] = mapped_column(Boolean, default=True)
    connection_state: Mapped[str] = mapped_column(
        String(16), default=NodeConnectionState.OFFLINE.value
    )
    operational_state: Mapped[str] = mapped_column(
        String(16), default=NodeOperationalState.IDLE.value
    )
    current_spot_id: Mapped[str | None] = mapped_column(String(36))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
