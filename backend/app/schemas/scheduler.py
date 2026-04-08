from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import ApiModel


class SchedulerConfigUpdate(ApiModel):
    enabled: bool = False
    interval_minutes: int = Field(ge=1)
    spot_sequence: list[str] = Field(default_factory=list)
    expected_revision: int | None = None


class SchedulerConfigResponse(ApiModel):
    enabled: bool
    interval_minutes: int
    current_index: int
    spot_sequence: list[str]
    revision: int
    next_run_at: datetime | None = None
    last_triggered_at: datetime | None = None


class SchedulerActionResponse(ApiModel):
    message: str
