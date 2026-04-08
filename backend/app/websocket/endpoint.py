from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from ..schemas.websocket import RegisterAckPayload
from .auth import authenticate_node
from .handlers import build_error_payload, handle_incoming_message
from .protocol import ProtocolError, build_message, parse_incoming_message


router = APIRouter()


@router.websocket("/ws/nodes")
async def node_websocket(websocket: WebSocket) -> None:
    app = websocket.app
    settings = app.state.settings
    await websocket.accept()

    authenticated_node_id: str | None = None

    try:
        initial_raw_message = await websocket.receive_json()
        envelope, hello_payload = parse_incoming_message(
            initial_raw_message,
            settings.protocol_version,
            settings.protocol_minor_version,
        )
        if envelope.type != "HELLO":
            raise ProtocolError("The first message must be HELLO")

        with app.state.session_factory() as db:
            node, sync_required = authenticate_node(
                db, app.state.node_service, hello_payload
            )

        authenticated_node_id = node.id
        await app.state.connection_manager.connect(authenticated_node_id, websocket)
        await websocket.send_json(
            build_message(
                "REGISTER_ACK",
                RegisterAckPayload(
                    node_id=node.id,
                    enabled=node.enabled,
                    autoplay_selected=node.autoplay_selected,
                    sync_required=sync_required,
                ),
                protocol_version=settings.protocol_version,
                protocol_minor_version=settings.protocol_minor_version,
            )
        )

        if sync_required:
            with app.state.session_factory() as db:
                sync_payload = app.state.spot_service.build_sync_payload(
                    db, authenticated_node_id
                )
            if sync_payload.spots:
                await websocket.send_json(
                    build_message(
                        "SYNC_REQUIRED",
                        sync_payload,
                        protocol_version=settings.protocol_version,
                        protocol_minor_version=settings.protocol_minor_version,
                        request_id=f"sync-{uuid.uuid4().hex[:12]}",
                    )
                )

        while True:
            raw_message = await websocket.receive_json()
            envelope, payload = parse_incoming_message(
                raw_message,
                settings.protocol_version,
                settings.protocol_minor_version,
            )
            await handle_incoming_message(app, envelope, payload, authenticated_node_id)

    except WebSocketDisconnect:
        pass
    except HTTPException as exc:
        await websocket.send_json(
            build_message(
                "ERROR",
                build_error_payload("UNAUTHORIZED", str(exc.detail)),
                protocol_version=settings.protocol_version,
                protocol_minor_version=settings.protocol_minor_version,
            )
        )
        await websocket.close(code=1008)
    except ProtocolError as exc:
        await websocket.send_json(
            build_message(
                "ERROR",
                build_error_payload("INVALID_MESSAGE", str(exc)),
                protocol_version=settings.protocol_version,
                protocol_minor_version=settings.protocol_minor_version,
            )
        )
        await websocket.close(code=1008)
    finally:
        if authenticated_node_id is not None:
            await app.state.connection_manager.disconnect(authenticated_node_id)
            with app.state.session_factory() as db:
                app.state.node_service.mark_disconnected(db, authenticated_node_id)
