from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.security import generate_token, hash_secret, verify_secret
from ..models.node import Node
from ..models.node_enrollment import NodeEnrollment
from ..models.spot import Spot
from ..schemas.node import NodeProvisionRequest
from ..schemas.websocket import (
    HelloPayload,
    HeartbeatPayload,
    PlaybackErrorPayload,
    PlaybackFinishedPayload,
    PlaybackStartedPayload,
    PlaybackStoppedPayload,
    StatusUpdatePayload,
    SyncResultPayload,
)
from ..utils.enums import NodeConnectionState, NodeOperationalState
from ..utils.time import utc_now
from .event_service import EventService


class NodeService:
    def __init__(self, settings: Settings, event_service: EventService) -> None:
        self.settings = settings
        self.event_service = event_service

    def list_nodes(self, db: Session) -> list[Node]:
        return list(db.scalars(select(Node).order_by(Node.id)))

    def get_node(self, db: Session, node_id: str) -> Node:
        node = db.get(Node, node_id)
        if node is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown node {node_id}",
            )
        return node

    def provision_node(
        self,
        db: Session,
        payload: NodeProvisionRequest,
        *,
        actor_id: str,
    ) -> tuple[Node, str]:
        raw_token = generate_token(24)
        node = self.provision_node_with_token(
            db,
            payload,
            raw_token=raw_token,
            actor_id=actor_id,
        )
        db.refresh(node)
        return node, raw_token

    def provision_node_with_token(
        self,
        db: Session,
        payload: NodeProvisionRequest,
        *,
        raw_token: str,
        actor_id: str,
    ) -> Node:
        node = db.get(Node, payload.node_id)
        if node is None:
            node = Node(
                id=payload.node_id,
                display_name=payload.display_name,
                auth_token_hash=hash_secret(raw_token),
                enabled=payload.enabled,
                autoplay_selected=payload.autoplay_selected,
                connection_state=NodeConnectionState.OFFLINE.value,
                operational_state=NodeOperationalState.IDLE.value,
            )
            db.add(node)
        else:
            node.display_name = payload.display_name
            node.auth_token_hash = hash_secret(raw_token)
            node.enabled = payload.enabled
            node.autoplay_selected = payload.autoplay_selected

        self.event_service.log(
            db,
            "NODE_PROVISIONED",
            details=f"Provisioned or rotated token for node {payload.node_id}",
            node_id=payload.node_id,
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        return node

    def reset_runtime_state(self, db: Session) -> None:
        for node in db.scalars(select(Node)):
            node.connection_state = NodeConnectionState.OFFLINE.value
            node.operational_state = NodeOperationalState.IDLE.value
            node.current_spot_id = None
        db.commit()

    def handle_hello(self, db: Session, payload: HelloPayload) -> tuple[Node, bool]:
        node = db.get(Node, payload.node_id)
        if node is None or not verify_secret(payload.auth_token, node.auth_token_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid node credentials",
            )

        node.display_name = payload.display_name
        node.platform = payload.platform
        node.app_version = payload.app_version
        node.device_model = payload.device_model
        node.connection_state = NodeConnectionState.ONLINE.value
        node.operational_state = NodeOperationalState.IDLE.value
        node.last_seen_at = utc_now()
        node.last_heartbeat_at = utc_now()

        active_spot_count = db.scalar(
            select(func.count()).select_from(Spot).where(Spot.active.is_(True))
        )
        self.event_service.log(
            db,
            "NODE_CONNECTED",
            details=f"Node {node.id} connected",
            node_id=node.id,
            actor_type="node",
            actor_id=node.id,
        )
        enrollment = db.scalar(
            select(NodeEnrollment)
            .where(
                NodeEnrollment.node_id == node.id,
                NodeEnrollment.status == "approved",
            )
            .order_by(NodeEnrollment.created_at.desc())
            .limit(1)
        )
        if enrollment is not None:
            enrollment.status = "enrolled"
            if enrollment.claimed_at is None:
                enrollment.claimed_at = utc_now()
            enrollment.approved_auth_token = None
        db.commit()
        db.refresh(node)
        return node, bool(active_spot_count)

    def handle_heartbeat(self, db: Session, payload: HeartbeatPayload) -> Node:
        node = self.get_node(db, payload.node_id)
        node.connection_state = NodeConnectionState.ONLINE.value
        node.operational_state = payload.status
        node.current_spot_id = payload.current_spot_id
        node.last_seen_at = utc_now()
        node.last_heartbeat_at = utc_now()
        db.commit()
        db.refresh(node)
        return node

    def handle_status_update(self, db: Session, payload: StatusUpdatePayload) -> Node:
        node = self.get_node(db, payload.node_id)
        node.connection_state = NodeConnectionState.ONLINE.value
        node.operational_state = payload.status
        node.current_spot_id = payload.current_spot_id
        node.last_seen_at = utc_now()
        if payload.details:
            node.last_error = payload.details if payload.status == "error" else None
        self.event_service.log(
            db,
            "NODE_STATUS_UPDATED",
            details=payload.details or f"Node state changed to {payload.status}",
            node_id=node.id,
            actor_type="node",
            actor_id=node.id,
        )
        db.commit()
        db.refresh(node)
        return node

    def handle_sync_result(self, db: Session, payload: SyncResultPayload) -> Node:
        node = self.get_node(db, payload.node_id)
        node.connection_state = NodeConnectionState.ONLINE.value
        node.last_seen_at = utc_now()
        node.last_heartbeat_at = utc_now()
        node.operational_state = (
            NodeOperationalState.READY.value
            if payload.result == "success"
            else NodeOperationalState.ERROR.value
        )
        node.last_error = payload.error_message
        self.event_service.log(
            db,
            "SYNC_RESULT",
            details=payload.error_message or f"Sync result: {payload.result}",
            node_id=node.id,
            actor_type="node",
            actor_id=node.id,
        )
        db.commit()
        db.refresh(node)
        return node

    def handle_playback_started(
        self, db: Session, payload: PlaybackStartedPayload
    ) -> Node:
        node = self.get_node(db, payload.node_id)
        node.connection_state = NodeConnectionState.ONLINE.value
        node.operational_state = NodeOperationalState.PLAYING.value
        node.current_spot_id = payload.spot_id
        node.last_seen_at = utc_now()
        self.event_service.log(
            db,
            "PLAYBACK_STARTED",
            details=f"Playback started for {payload.spot_id}",
            node_id=node.id,
            spot_id=payload.spot_id,
            actor_type="node",
            actor_id=node.id,
        )
        db.commit()
        db.refresh(node)
        return node

    def handle_playback_finished(
        self, db: Session, payload: PlaybackFinishedPayload
    ) -> Node:
        node = self.get_node(db, payload.node_id)
        node.connection_state = NodeConnectionState.ONLINE.value
        node.operational_state = NodeOperationalState.READY.value
        node.current_spot_id = None
        node.last_seen_at = utc_now()
        self.event_service.log(
            db,
            "PLAYBACK_FINISHED",
            details=f"Playback finished for {payload.spot_id}",
            node_id=node.id,
            spot_id=payload.spot_id,
            actor_type="node",
            actor_id=node.id,
        )
        db.commit()
        db.refresh(node)
        return node

    def handle_playback_stopped(
        self, db: Session, payload: PlaybackStoppedPayload
    ) -> Node:
        node = self.get_node(db, payload.node_id)
        node.connection_state = NodeConnectionState.ONLINE.value
        node.operational_state = NodeOperationalState.STOPPED.value
        node.current_spot_id = None
        node.last_seen_at = utc_now()
        self.event_service.log(
            db,
            "PLAYBACK_STOPPED",
            details=payload.reason or "Playback stopped",
            node_id=node.id,
            spot_id=payload.spot_id,
            actor_type="node",
            actor_id=node.id,
        )
        db.commit()
        db.refresh(node)
        return node

    def handle_playback_error(self, db: Session, payload: PlaybackErrorPayload) -> Node:
        node = self.get_node(db, payload.node_id)
        node.connection_state = NodeConnectionState.ONLINE.value
        node.operational_state = NodeOperationalState.ERROR.value
        node.last_error = payload.error_message
        node.last_seen_at = utc_now()
        self.event_service.log(
            db,
            "PLAYBACK_ERROR",
            details=f"{payload.error_code}: {payload.error_message}",
            node_id=node.id,
            spot_id=payload.spot_id,
            actor_type="node",
            actor_id=node.id,
        )
        db.commit()
        db.refresh(node)
        return node

    def set_enabled(
        self, db: Session, node_id: str, enabled: bool, *, actor_id: str
    ) -> Node:
        node = self.get_node(db, node_id)
        node.enabled = enabled
        self.event_service.log(
            db,
            "NODE_ENABLED_CHANGED",
            details=f"Node enabled set to {enabled}",
            node_id=node_id,
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(node)
        return node

    def set_autoplay_selected(
        self, db: Session, node_id: str, autoplay_selected: bool, *, actor_id: str
    ) -> Node:
        node = self.get_node(db, node_id)
        node.autoplay_selected = autoplay_selected
        self.event_service.log(
            db,
            "NODE_AUTOPLAY_CHANGED",
            details=f"Node autoplaySelected set to {autoplay_selected}",
            node_id=node_id,
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(node)
        return node

    def mark_disconnected(self, db: Session, node_id: str) -> Node | None:
        node = db.get(Node, node_id)
        if node is None:
            return None
        node.connection_state = NodeConnectionState.OFFLINE.value
        node.operational_state = NodeOperationalState.IDLE.value
        node.current_spot_id = None
        self.event_service.log(
            db,
            "NODE_DISCONNECTED",
            details=f"Node {node_id} disconnected",
            node_id=node_id,
            actor_type="node",
            actor_id=node_id,
        )
        db.commit()
        db.refresh(node)
        return node

    def sweep_liveness(self, db: Session) -> list[str]:
        now = utc_now()
        changed_nodes: list[str] = []
        for node in db.scalars(select(Node)):
            reference_time = node.last_heartbeat_at or node.last_seen_at
            if reference_time is None:
                continue
            elapsed = (now - reference_time).total_seconds()
            if elapsed >= self.settings.heartbeat_offline_after_seconds:
                if node.connection_state != NodeConnectionState.OFFLINE.value:
                    node.connection_state = NodeConnectionState.OFFLINE.value
                    node.operational_state = NodeOperationalState.IDLE.value
                    node.current_spot_id = None
                    changed_nodes.append(node.id)
                    self.event_service.log(
                        db,
                        "NODE_OFFLINE",
                        details="Node marked offline after heartbeat timeout",
                        node_id=node.id,
                        actor_type="system",
                        actor_id="heartbeat-monitor",
                    )
            elif elapsed >= self.settings.heartbeat_stale_after_seconds:
                if node.connection_state != NodeConnectionState.STALE.value:
                    node.connection_state = NodeConnectionState.STALE.value
                    changed_nodes.append(node.id)
                    self.event_service.log(
                        db,
                        "NODE_STALE",
                        details="Node marked stale after missed heartbeat",
                        node_id=node.id,
                        actor_type="system",
                        actor_id="heartbeat-monitor",
                    )
            elif node.connection_state != NodeConnectionState.ONLINE.value:
                node.connection_state = NodeConnectionState.ONLINE.value
                changed_nodes.append(node.id)
        if changed_nodes:
            db.commit()
        return changed_nodes

    def get_autoplay_target_node_ids(self, db: Session) -> list[str]:
        query = select(Node.id).where(
            Node.enabled.is_(True),
            Node.autoplay_selected.is_(True),
            Node.connection_state == NodeConnectionState.ONLINE.value,
        )
        return list(db.scalars(query))
