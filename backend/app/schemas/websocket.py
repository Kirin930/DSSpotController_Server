from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .common import ApiModel


class WsEnvelope(ApiModel):
    type: str
    protocol_version: int | float | str = 1
    timestamp: datetime
    request_id: str | None = None
    payload: dict[str, Any]


class HelloPayload(ApiModel):
    node_id: str
    auth_token: str
    display_name: str
    platform: str = "android"
    app_version: str | None = None
    device_model: str | None = None


class HeartbeatPayload(ApiModel):
    node_id: str
    status: str
    current_spot_id: str | None = None


class StatusUpdatePayload(ApiModel):
    node_id: str
    status: str
    current_spot_id: str | None = None
    details: str | None = None


class SyncResultPayload(ApiModel):
    node_id: str
    result: str
    downloaded_spot_ids: list[str] = Field(default_factory=list)
    updated_spot_ids: list[str] = Field(default_factory=list)
    failed_spot_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None


class PlaybackStartedPayload(ApiModel):
    node_id: str
    spot_id: str


class PlaybackFinishedPayload(ApiModel):
    node_id: str
    spot_id: str
    duration_ms: int


class PlaybackStoppedPayload(ApiModel):
    node_id: str
    spot_id: str | None = None
    reason: str | None = None


class PlaybackErrorPayload(ApiModel):
    node_id: str
    spot_id: str | None = None
    error_code: str
    error_message: str


class ErrorPayload(ApiModel):
    node_id: str | None = None
    error_code: str
    error_message: str


class RegisterAckPayload(ApiModel):
    node_id: str
    enabled: bool
    autoplay_selected: bool
    sync_required: bool


class SyncSpotPayload(ApiModel):
    spot_id: str
    title: str
    version: int
    checksum: str
    download_url: str


class SyncRequiredPayload(ApiModel):
    spots: list[SyncSpotPayload]


class PlayPayload(ApiModel):
    spot_id: str
    replace_if_playing: bool = True


class StopPayload(ApiModel):
    pass


class SetEnabledPayload(ApiModel):
    enabled: bool


class ConfigUpdatePayload(ApiModel):
    autoplay_selected: bool | None = None
