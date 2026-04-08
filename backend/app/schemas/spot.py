from __future__ import annotations

from datetime import datetime

from .common import ApiModel


class SpotResponse(ApiModel):
    id: str
    title: str
    filename: str
    version: int
    checksum: str
    active: bool
    mime_type: str
    duration_ms: int | None = None
    created_at: datetime


class SpotUpdateRequest(ApiModel):
    title: str | None = None
    active: bool | None = None
