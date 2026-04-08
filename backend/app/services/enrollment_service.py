from __future__ import annotations

import secrets
from datetime import timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..models.node import Node
from ..models.node_enrollment import NodeEnrollment
from ..schemas.node import (
    NodeEnrollmentApproveRequest,
    NodeEnrollmentRejectRequest,
    NodeEnrollmentRequestCreate,
    NodeProvisionRequest,
)
from ..utils.time import utc_now
from .event_service import EventService
from .node_service import NodeService


class EnrollmentService:
    def __init__(
        self,
        settings: Settings,
        event_service: EventService,
        node_service: NodeService,
    ) -> None:
        self.settings = settings
        self.event_service = event_service
        self.node_service = node_service

    def _generate_pairing_code(self) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return "".join(
            secrets.choice(alphabet) for _ in range(self.settings.enrollment_code_length)
        )

    def _mark_expired_if_needed(self, enrollment: NodeEnrollment) -> None:
        expires_at = enrollment.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if enrollment.status == "pending" and expires_at < utc_now():
            enrollment.status = "expired"

    def request_enrollment(
        self, db: Session, payload: NodeEnrollmentRequestCreate
    ) -> NodeEnrollment:
        existing_node = db.get(Node, payload.node_id)
        if existing_node is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Node is already enrolled; use admin provisioning to rotate credentials",
            )

        existing_pending = db.scalar(
            select(NodeEnrollment)
            .where(
                NodeEnrollment.node_id == payload.node_id,
                NodeEnrollment.status == "pending",
            )
            .order_by(NodeEnrollment.created_at.desc())
            .limit(1)
        )

        pairing_code = self._generate_pairing_code()
        expires_at = utc_now() + timedelta(seconds=self.settings.enrollment_ttl_seconds)
        if existing_pending is None:
            enrollment = NodeEnrollment(
                node_id=payload.node_id,
                pairing_code=pairing_code,
                display_name=payload.display_name,
                platform=payload.platform,
                app_version=payload.app_version,
                device_model=payload.device_model,
                expires_at=expires_at,
                status="pending",
            )
            db.add(enrollment)
        else:
            enrollment = existing_pending
            enrollment.pairing_code = pairing_code
            enrollment.display_name = payload.display_name
            enrollment.platform = payload.platform
            enrollment.app_version = payload.app_version
            enrollment.device_model = payload.device_model
            enrollment.expires_at = expires_at
            enrollment.rejection_reason = None

        self.event_service.log(
            db,
            "NODE_ENROLLMENT_REQUESTED",
            details=f"Enrollment requested for node {payload.node_id}",
            node_id=payload.node_id,
            actor_type="node",
            actor_id=payload.node_id,
        )
        db.commit()
        db.refresh(enrollment)
        return enrollment

    def list_enrollments(
        self, db: Session, *, status_filter: str | None = None
    ) -> list[NodeEnrollment]:
        query = select(NodeEnrollment).order_by(NodeEnrollment.created_at.desc())
        if status_filter:
            query = query.where(NodeEnrollment.status == status_filter)
        enrollments = list(db.scalars(query))
        changed = False
        for enrollment in enrollments:
            previous_status = enrollment.status
            self._mark_expired_if_needed(enrollment)
            changed = changed or previous_status != enrollment.status
        if changed:
            db.commit()
        return enrollments

    def get_enrollment(self, db: Session, enrollment_id: str) -> NodeEnrollment:
        enrollment = db.get(NodeEnrollment, enrollment_id)
        if enrollment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown enrollment request {enrollment_id}",
            )
        previous_status = enrollment.status
        self._mark_expired_if_needed(enrollment)
        if previous_status != enrollment.status:
            db.commit()
            db.refresh(enrollment)
        return enrollment

    def approve_enrollment(
        self,
        db: Session,
        enrollment_id: str,
        payload: NodeEnrollmentApproveRequest,
        *,
        actor_id: str,
    ) -> NodeEnrollment:
        enrollment = self.get_enrollment(db, enrollment_id)
        if enrollment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Enrollment request is {enrollment.status}",
            )

        provision_request = NodeProvisionRequest(
            node_id=enrollment.node_id,
            display_name=payload.display_name or enrollment.display_name,
            enabled=payload.enabled,
            autoplay_selected=payload.autoplay_selected,
        )
        node, raw_token = self.node_service.provision_node(
            db,
            provision_request,
            actor_id=actor_id,
        )
        enrollment.status = "approved"
        enrollment.display_name = node.display_name
        enrollment.enabled = node.enabled
        enrollment.autoplay_selected = node.autoplay_selected
        enrollment.approved_auth_token = raw_token
        enrollment.approved_at = utc_now()
        enrollment.approved_by = actor_id
        enrollment.rejection_reason = None
        self.event_service.log(
            db,
            "NODE_ENROLLMENT_APPROVED",
            details=f"Enrollment approved for node {enrollment.node_id}",
            node_id=enrollment.node_id,
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(enrollment)
        return enrollment

    def reject_enrollment(
        self,
        db: Session,
        enrollment_id: str,
        payload: NodeEnrollmentRejectRequest,
        *,
        actor_id: str,
    ) -> NodeEnrollment:
        enrollment = self.get_enrollment(db, enrollment_id)
        if enrollment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Enrollment request is {enrollment.status}",
            )

        enrollment.status = "rejected"
        enrollment.rejected_at = utc_now()
        enrollment.rejected_by = actor_id
        enrollment.rejection_reason = payload.reason
        self.event_service.log(
            db,
            "NODE_ENROLLMENT_REJECTED",
            details=payload.reason or f"Enrollment rejected for node {enrollment.node_id}",
            node_id=enrollment.node_id,
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(enrollment)
        return enrollment

    def get_status_for_node(
        self,
        db: Session,
        enrollment_id: str,
        *,
        pairing_code: str,
    ) -> NodeEnrollment:
        enrollment = self.get_enrollment(db, enrollment_id)
        if enrollment.pairing_code != pairing_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid pairing code",
            )
        if enrollment.status == "approved" and enrollment.claimed_at is None:
            enrollment.claimed_at = utc_now()
            db.commit()
            db.refresh(enrollment)
        return enrollment
