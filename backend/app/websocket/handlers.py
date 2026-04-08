from __future__ import annotations

from fastapi import HTTPException

from ..schemas.websocket import ErrorPayload
from .protocol import ProtocolError


async def handle_incoming_message(app, envelope, payload, authenticated_node_id: str):
    payload_node_id = getattr(payload, "node_id", None)
    if payload_node_id is not None and payload_node_id != authenticated_node_id:
        raise ProtocolError("Node ID mismatch")

    with app.state.session_factory() as db:
        node_service = app.state.node_service
        if envelope.type == "HEARTBEAT":
            node_service.handle_heartbeat(db, payload)
        elif envelope.type == "STATUS_UPDATE":
            node_service.handle_status_update(db, payload)
        elif envelope.type == "SYNC_RESULT":
            node_service.handle_sync_result(db, payload)
        elif envelope.type == "PLAYBACK_STARTED":
            node_service.handle_playback_started(db, payload)
        elif envelope.type == "PLAYBACK_FINISHED":
            node_service.handle_playback_finished(db, payload)
        elif envelope.type == "PLAYBACK_STOPPED":
            node_service.handle_playback_stopped(db, payload)
        elif envelope.type == "PLAYBACK_ERROR":
            node_service.handle_playback_error(db, payload)
        elif envelope.type == "ERROR":
            app.state.event_service.log(
                db,
                "NODE_PROTOCOL_ERROR",
                details=f"{payload.error_code}: {payload.error_message}",
                node_id=authenticated_node_id,
                actor_type="node",
                actor_id=authenticated_node_id,
            )
            db.commit()
        else:
            raise HTTPException(status_code=400, detail="Unhandled message type")

    if envelope.request_id:
        app.state.connection_manager.resolve_ack(
            authenticated_node_id,
            envelope.request_id,
            envelope.type,
            payload.model_dump(by_alias=True, mode="json"),
        )


def build_error_payload(error_code: str, error_message: str) -> ErrorPayload:
    return ErrorPayload(error_code=error_code, error_message=error_message)
