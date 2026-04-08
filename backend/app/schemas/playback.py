from __future__ import annotations

from .common import ApiModel


class PlaybackPlayRequest(ApiModel):
    spot_id: str
    node_ids: list[str]
    replace_if_playing: bool = True


class PlaybackStopRequest(ApiModel):
    node_ids: list[str]


class NodeCommandResult(ApiModel):
    node_id: str
    status: str
    detail: str | None = None


class PlaybackCommandResponse(ApiModel):
    message: str
    spot_id: str | None = None
    node_ids: list[str]
    results: list[NodeCommandResult]
