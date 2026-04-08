from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..deps import (
    get_connection_manager,
    get_current_admin,
    get_db,
    get_enrollment_service,
    get_node_service,
    get_playback_service,
    require_current_admin_write,
)
from ...models.admin_user import AdminUser
from ...schemas.node import (
    NodeAutoplayUpdate,
    NodeEnabledUpdate,
    NodeEnrollmentApproveRequest,
    NodeEnrollmentListResponse,
    NodeEnrollmentRejectRequest,
    NodeEnrollmentRequestCreate,
    NodeEnrollmentResponse,
    NodeEnrollmentStatusResponse,
    NodeProvisionRequest,
    NodeProvisionResponse,
    NodeResponse,
    NodeSyncResponse,
)
from ...schemas.websocket import ConfigUpdatePayload, SetEnabledPayload
from ...services.enrollment_service import EnrollmentService
from ...services.node_service import NodeService
from ...services.playback_service import PlaybackService
from ...websocket.protocol import build_message


router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("", response_model=list[NodeResponse])
def list_nodes(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
    node_service: NodeService = Depends(get_node_service),
) -> list[NodeResponse]:
    return [NodeResponse.model_validate(node) for node in node_service.list_nodes(db)]


@router.post("/provision", response_model=NodeProvisionResponse)
def provision_node(
    payload: NodeProvisionRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    node_service: NodeService = Depends(get_node_service),
) -> NodeProvisionResponse:
    node, auth_token = node_service.provision_node(
        db, payload, actor_id=current_admin.username
    )
    return NodeProvisionResponse(
        id=node.id,
        display_name=node.display_name,
        auth_token=auth_token,
        enabled=node.enabled,
        autoplay_selected=node.autoplay_selected,
    )


@router.post("/enrollments/request", response_model=NodeEnrollmentResponse)
def request_enrollment(
    payload: NodeEnrollmentRequestCreate,
    db: Session = Depends(get_db),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> NodeEnrollmentResponse:
    enrollment = enrollment_service.request_enrollment(db, payload)
    return NodeEnrollmentResponse.model_validate(enrollment)


@router.get("/enrollments", response_model=NodeEnrollmentListResponse)
def list_enrollments(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> NodeEnrollmentListResponse:
    items = enrollment_service.list_enrollments(db, status_filter=status)
    return NodeEnrollmentListResponse(
        items=[NodeEnrollmentResponse.model_validate(item) for item in items]
    )


@router.get("/enrollments/{enrollment_id}", response_model=NodeEnrollmentResponse)
def get_enrollment(
    enrollment_id: str,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> NodeEnrollmentResponse:
    return NodeEnrollmentResponse.model_validate(
        enrollment_service.get_enrollment(db, enrollment_id)
    )


@router.post(
    "/enrollments/{enrollment_id}/approve",
    response_model=NodeEnrollmentResponse,
)
def approve_enrollment(
    enrollment_id: str,
    payload: NodeEnrollmentApproveRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> NodeEnrollmentResponse:
    enrollment = enrollment_service.approve_enrollment(
        db, enrollment_id, payload, actor_id=current_admin.username
    )
    return NodeEnrollmentResponse.model_validate(enrollment)


@router.post(
    "/enrollments/{enrollment_id}/reject",
    response_model=NodeEnrollmentResponse,
)
def reject_enrollment(
    enrollment_id: str,
    payload: NodeEnrollmentRejectRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> NodeEnrollmentResponse:
    enrollment = enrollment_service.reject_enrollment(
        db, enrollment_id, payload, actor_id=current_admin.username
    )
    return NodeEnrollmentResponse.model_validate(enrollment)


@router.get(
    "/enrollments/{enrollment_id}/status",
    response_model=NodeEnrollmentStatusResponse,
)
def enrollment_status(
    enrollment_id: str,
    pairing_code: str,
    db: Session = Depends(get_db),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> NodeEnrollmentStatusResponse:
    enrollment = enrollment_service.get_status_for_node(
        db, enrollment_id, pairing_code=pairing_code
    )
    return NodeEnrollmentStatusResponse(
        id=enrollment.id,
        node_id=enrollment.node_id,
        pairing_code=enrollment.pairing_code,
        status=enrollment.status,
        auth_token=enrollment.approved_auth_token,
        expires_at=enrollment.expires_at,
        rejection_reason=enrollment.rejection_reason,
    )


@router.get("/{node_id}", response_model=NodeResponse)
def get_node(
    node_id: str,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
    node_service: NodeService = Depends(get_node_service),
) -> NodeResponse:
    return NodeResponse.model_validate(node_service.get_node(db, node_id))


@router.patch("/{node_id}/enabled", response_model=NodeResponse)
async def update_enabled(
    node_id: str,
    payload: NodeEnabledUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    node_service: NodeService = Depends(get_node_service),
    connection_manager=Depends(get_connection_manager),
) -> NodeResponse:
    node = node_service.set_enabled(
        db, node_id, payload.enabled, actor_id=current_admin.username
    )
    if connection_manager.is_connected(node_id):
        await connection_manager.send_to_node(
            node_id,
            build_message(
                "SET_ENABLED",
                SetEnabledPayload(enabled=payload.enabled),
                protocol_version=request.app.state.settings.protocol_version,
                protocol_minor_version=request.app.state.settings.protocol_minor_version,
            ),
        )
    return NodeResponse.model_validate(node)


@router.patch("/{node_id}/autoplay", response_model=NodeResponse)
async def update_autoplay(
    node_id: str,
    payload: NodeAutoplayUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_current_admin_write),
    node_service: NodeService = Depends(get_node_service),
    connection_manager=Depends(get_connection_manager),
) -> NodeResponse:
    node = node_service.set_autoplay_selected(
        db, node_id, payload.autoplay_selected, actor_id=current_admin.username
    )
    if connection_manager.is_connected(node_id):
        await connection_manager.send_to_node(
            node_id,
            build_message(
                "CONFIG_UPDATE",
                ConfigUpdatePayload(autoplay_selected=payload.autoplay_selected),
                protocol_version=request.app.state.settings.protocol_version,
                protocol_minor_version=request.app.state.settings.protocol_minor_version,
            ),
        )
    return NodeResponse.model_validate(node)


@router.post("/{node_id}/sync", response_model=NodeSyncResponse)
async def request_sync(
    node_id: str,
    playback_service: PlaybackService = Depends(get_playback_service),
    _: AdminUser = Depends(require_current_admin_write),
) -> NodeSyncResponse:
    request_id = await playback_service.request_sync(node_id)
    return NodeSyncResponse(
        message="Sync requested",
        node_id=node_id,
        request_id=request_id,
    )
