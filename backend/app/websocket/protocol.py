from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..core.security import serialize_for_json
from ..schemas.websocket import (
    ErrorPayload,
    HeartbeatPayload,
    HelloPayload,
    PlaybackErrorPayload,
    PlaybackFinishedPayload,
    PlaybackStartedPayload,
    PlaybackStoppedPayload,
    StatusUpdatePayload,
    SyncResultPayload,
    WsEnvelope,
)
from ..utils.time import utc_now


INCOMING_PAYLOAD_MODELS = {
    "HELLO": HelloPayload,
    "HEARTBEAT": HeartbeatPayload,
    "STATUS_UPDATE": StatusUpdatePayload,
    "SYNC_RESULT": SyncResultPayload,
    "PLAYBACK_STARTED": PlaybackStartedPayload,
    "PLAYBACK_FINISHED": PlaybackFinishedPayload,
    "PLAYBACK_STOPPED": PlaybackStoppedPayload,
    "PLAYBACK_ERROR": PlaybackErrorPayload,
    "ERROR": ErrorPayload,
}


class ProtocolError(Exception):
    pass


def parse_protocol_version(raw_version: int | float | str) -> tuple[int, int]:
    if isinstance(raw_version, int):
        return raw_version, 0
    if isinstance(raw_version, float):
        return parse_protocol_version(f"{raw_version}")
    if isinstance(raw_version, str):
        parts = raw_version.split(".", maxsplit=1)
        if len(parts) == 1:
            return int(parts[0]), 0
        return int(parts[0]), int(parts[1])
    raise ProtocolError("Unsupported protocol version format")


def format_protocol_version(major: int, minor: int) -> int | str:
    if minor == 0:
        return major
    return f"{major}.{minor}"


def parse_incoming_message(
    raw_message: dict[str, Any],
    protocol_version: int,
    protocol_minor_version: int = 0,
):
    try:
        envelope = WsEnvelope.model_validate(raw_message)
    except ValidationError as exc:
        raise ProtocolError("Invalid message envelope") from exc
    try:
        incoming_major, incoming_minor = parse_protocol_version(
            envelope.protocol_version
        )
    except (TypeError, ValueError) as exc:
        raise ProtocolError("Unsupported protocol version format") from exc
    if incoming_major != protocol_version:
        raise ProtocolError("Unsupported protocol major version")
    if incoming_minor < 0:
        raise ProtocolError("Unsupported protocol minor version")

    payload_model = INCOMING_PAYLOAD_MODELS.get(envelope.type)
    if payload_model is None:
        raise ProtocolError(f"Unsupported message type {envelope.type}")

    try:
        payload = payload_model.model_validate(envelope.payload)
    except ValidationError as exc:
        raise ProtocolError(f"Invalid payload for {envelope.type}") from exc
    return envelope, payload


def build_message(
    message_type: str,
    payload: Any,
    *,
    protocol_version: int,
    protocol_minor_version: int = 0,
    request_id: str | None = None,
) -> dict[str, Any]:
    envelope = WsEnvelope(
        type=message_type,
        protocol_version=format_protocol_version(
            protocol_version, protocol_minor_version
        ),
        timestamp=utc_now(),
        request_id=request_id,
        payload=serialize_for_json(payload),
    )
    return envelope.model_dump(by_alias=True, mode="json")
