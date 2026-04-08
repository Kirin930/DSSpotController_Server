from __future__ import annotations

import asyncio
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import Settings
from ..models.node import Node
from ..models.spot import Spot
from ..schemas.playback import NodeCommandResult, PlaybackCommandResponse
from ..schemas.websocket import PlayPayload
from ..websocket.manager import CommandAcknowledgement, ConnectionManager
from ..websocket.protocol import build_message
from .event_service import EventService
from .spot_service import SpotService


class PlaybackService:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        connection_manager: ConnectionManager,
        spot_service: SpotService,
        event_service: EventService,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.connection_manager = connection_manager
        self.spot_service = spot_service
        self.event_service = event_service
        self.scheduler_service = None

    def set_scheduler_service(self, scheduler_service) -> None:
        self.scheduler_service = scheduler_service

    def build_request_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    async def request_sync(self, node_id: str) -> str:
        with self.session_factory() as db:
            sync_payload = self.spot_service.build_sync_payload(db, node_id)
            request_id = self.build_request_id("sync")
            message = build_message(
                "SYNC_REQUIRED",
                sync_payload,
                protocol_version=self.settings.protocol_version,
                protocol_minor_version=self.settings.protocol_minor_version,
                request_id=request_id,
            )
            sent = await self.connection_manager.send_to_node(node_id, message)
            if not sent:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Node {node_id} is not currently connected",
                )

            self.event_service.log(
                db,
                "SYNC_REQUESTED",
                details=f"Sync requested for node {node_id}",
                node_id=node_id,
                actor_type="admin",
                actor_id="api",
            )
            db.commit()
            return request_id

    async def dispatch_play(
        self,
        spot_id: str,
        node_ids: list[str],
        *,
        replace_if_playing: bool,
        origin: str,
        actor_id: str,
        request_prefix: str = "play",
        reset_scheduler: bool = True,
    ) -> PlaybackCommandResponse:
        unique_node_ids = list(dict.fromkeys(node_ids))
        request_id = self.build_request_id(request_prefix)
        with self.session_factory() as db:
            spot = db.get(Spot, spot_id)
            if spot is None or not spot.active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Unknown active spot {spot_id}",
                )

            nodes = {node.id: node for node in self._load_nodes(db, unique_node_ids)}
            futures: dict[str, asyncio.Future[CommandAcknowledgement]] = {}
            results: list[NodeCommandResult] = []

            for node_id in unique_node_ids:
                node = nodes.get(node_id)
                if node is None:
                    results.append(
                        NodeCommandResult(
                            node_id=node_id,
                            status="missing",
                            detail="Unknown node",
                        )
                    )
                    continue
                if not node.enabled:
                    results.append(
                        NodeCommandResult(
                            node_id=node_id,
                            status="disabled",
                            detail="Node is disabled",
                        )
                    )
                    continue
                if not self.connection_manager.is_connected(node_id):
                    results.append(
                        NodeCommandResult(
                            node_id=node_id,
                            status="offline",
                            detail="Node is not connected",
                        )
                    )
                    continue

                future = self.connection_manager.create_ack_future(node_id, request_id)
                sent = await self.connection_manager.send_to_node(
                    node_id,
                    build_message(
                        "PLAY",
                        PlayPayload(
                            spot_id=spot_id,
                            replace_if_playing=replace_if_playing,
                        ),
                        protocol_version=self.settings.protocol_version,
                        protocol_minor_version=self.settings.protocol_minor_version,
                        request_id=request_id,
                    ),
                )
                if not sent:
                    self.connection_manager.cancel_ack(node_id, request_id)
                    results.append(
                        NodeCommandResult(
                            node_id=node_id,
                            status="offline",
                            detail="Node connection became unavailable",
                        )
                    )
                    continue

                futures[node_id] = future
                self.event_service.log(
                    db,
                    "PLAY_COMMAND_SENT",
                    details=f"Dispatching spot {spot_id} to node {node_id}",
                    node_id=node_id,
                    spot_id=spot_id,
                    actor_type=origin,
                    actor_id=actor_id,
                )

            db.commit()

        results.extend(await self._collect_play_results(request_id, futures))

        if (
            reset_scheduler
            and origin == "admin"
            and self.scheduler_service is not None
            and any(result.status == "started" for result in results)
        ):
            await self.scheduler_service.reset_after_manual_play(actor_id=actor_id)

        return PlaybackCommandResponse(
            message="Play command dispatched",
            spot_id=spot_id,
            node_ids=unique_node_ids,
            results=results,
        )

    async def dispatch_stop(
        self,
        node_ids: list[str],
        *,
        origin: str,
        actor_id: str,
        request_prefix: str = "stop",
    ) -> PlaybackCommandResponse:
        unique_node_ids = list(dict.fromkeys(node_ids))
        request_id = self.build_request_id(request_prefix)
        with self.session_factory() as db:
            nodes = {node.id: node for node in self._load_nodes(db, unique_node_ids)}
            futures: dict[str, asyncio.Future[CommandAcknowledgement]] = {}
            results: list[NodeCommandResult] = []

            for node_id in unique_node_ids:
                node = nodes.get(node_id)
                if node is None:
                    results.append(
                        NodeCommandResult(
                            node_id=node_id,
                            status="missing",
                            detail="Unknown node",
                        )
                    )
                    continue
                if not self.connection_manager.is_connected(node_id):
                    results.append(
                        NodeCommandResult(
                            node_id=node_id,
                            status="offline",
                            detail="Node is not connected",
                        )
                    )
                    continue

                future = self.connection_manager.create_ack_future(node_id, request_id)
                sent = await self.connection_manager.send_to_node(
                    node_id,
                    build_message(
                        "STOP",
                        {},
                        protocol_version=self.settings.protocol_version,
                        protocol_minor_version=self.settings.protocol_minor_version,
                        request_id=request_id,
                    ),
                )
                if not sent:
                    self.connection_manager.cancel_ack(node_id, request_id)
                    results.append(
                        NodeCommandResult(
                            node_id=node_id,
                            status="offline",
                            detail="Node connection became unavailable",
                        )
                    )
                    continue

                futures[node_id] = future
                self.event_service.log(
                    db,
                    "STOP_COMMAND_SENT",
                    details=f"Stop command sent to node {node_id}",
                    node_id=node_id,
                    actor_type=origin,
                    actor_id=actor_id,
                )

            db.commit()

        results.extend(await self._collect_stop_results(request_id, futures))
        return PlaybackCommandResponse(
            message="Stop command dispatched",
            node_ids=unique_node_ids,
            results=results,
        )

    def _load_nodes(self, db: Session, node_ids: list[str]) -> list[Node]:
        return [node for node_id in node_ids if (node := db.get(Node, node_id)) is not None]

    async def _collect_play_results(
        self,
        request_id: str,
        futures: dict[str, asyncio.Future[CommandAcknowledgement]],
    ) -> list[NodeCommandResult]:
        results: list[NodeCommandResult] = []
        for node_id, future in futures.items():
            try:
                acknowledgement = await asyncio.wait_for(
                    future, timeout=self.settings.command_ack_timeout_seconds
                )
            except (TimeoutError, asyncio.CancelledError):
                self.connection_manager.cancel_ack(node_id, request_id)
                results.append(
                    NodeCommandResult(
                        node_id=node_id,
                        status="timeout",
                        detail="Node did not acknowledge the play command in time",
                    )
                )
                continue

            results.append(self._play_result_from_ack(node_id, acknowledgement))
        return results

    async def _collect_stop_results(
        self,
        request_id: str,
        futures: dict[str, asyncio.Future[CommandAcknowledgement]],
    ) -> list[NodeCommandResult]:
        results: list[NodeCommandResult] = []
        for node_id, future in futures.items():
            try:
                acknowledgement = await asyncio.wait_for(
                    future, timeout=self.settings.command_ack_timeout_seconds
                )
            except (TimeoutError, asyncio.CancelledError):
                self.connection_manager.cancel_ack(node_id, request_id)
                results.append(
                    NodeCommandResult(
                        node_id=node_id,
                        status="timeout",
                        detail="Node did not acknowledge the stop command in time",
                    )
                )
                continue

            if acknowledgement.message_type == "PLAYBACK_STOPPED":
                results.append(
                    NodeCommandResult(node_id=node_id, status="stopped", detail=None)
                )
            elif acknowledgement.message_type == "ERROR":
                error_message = acknowledgement.payload.get(
                    "errorMessage", "Node rejected the stop command"
                )
                results.append(
                    NodeCommandResult(
                        node_id=node_id,
                        status="error",
                        detail=error_message,
                    )
                )
            else:
                results.append(
                    NodeCommandResult(
                        node_id=node_id,
                        status="acknowledged",
                        detail="Node acknowledged the stop command",
                    )
                )
        return results

    def _play_result_from_ack(
        self, node_id: str, acknowledgement: CommandAcknowledgement
    ) -> NodeCommandResult:
        if acknowledgement.message_type == "PLAYBACK_STARTED":
            return NodeCommandResult(node_id=node_id, status="started", detail=None)
        if acknowledgement.message_type in {"PLAYBACK_ERROR", "ERROR"}:
            return NodeCommandResult(
                node_id=node_id,
                status="error",
                detail=acknowledgement.payload.get(
                    "errorMessage", "Node reported a playback error"
                ),
            )
        return NodeCommandResult(
            node_id=node_id,
            status="acknowledged",
            detail="Node acknowledged the play command",
        )
