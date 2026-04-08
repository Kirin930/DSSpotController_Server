from __future__ import annotations

from datetime import datetime

from .common import ApiModel


class NodeResponse(ApiModel):
    id: str
    display_name: str
    enabled: bool
    autoplay_selected: bool
    connection_state: str
    operational_state: str
    current_spot_id: str | None = None
    last_seen_at: datetime | None = None
    app_version: str | None = None
    platform: str | None = None
    device_model: str | None = None


class NodeEnabledUpdate(ApiModel):
    enabled: bool


class NodeAutoplayUpdate(ApiModel):
    autoplay_selected: bool


class NodeProvisionRequest(ApiModel):
    node_id: str
    display_name: str
    enabled: bool = True
    autoplay_selected: bool = True


class NodeProvisionResponse(ApiModel):
    id: str
    display_name: str
    auth_token: str
    enabled: bool
    autoplay_selected: bool


class NodeSyncResponse(ApiModel):
    message: str
    node_id: str
    request_id: str


class NodeEnrollmentRequestCreate(ApiModel):
    node_id: str
    display_name: str
    platform: str = "android"
    app_version: str | None = None
    device_model: str | None = None


class NodeEnrollmentResponse(ApiModel):
    id: str
    node_id: str
    pairing_code: str
    status: str
    display_name: str
    platform: str
    app_version: str | None = None
    device_model: str | None = None
    enabled: bool
    autoplay_selected: bool
    expires_at: datetime
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None


class NodeEnrollmentListResponse(ApiModel):
    items: list[NodeEnrollmentResponse]


class NodeEnrollmentApproveRequest(ApiModel):
    enabled: bool = True
    autoplay_selected: bool = True
    display_name: str | None = None


class NodeEnrollmentRejectRequest(ApiModel):
    reason: str | None = None


class NodeEnrollmentStatusResponse(ApiModel):
    id: str
    node_id: str
    pairing_code: str
    status: str
    auth_token: str | None = None
    expires_at: datetime
    rejection_reason: str | None = None
