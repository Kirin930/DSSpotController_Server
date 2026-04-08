from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_playback_service, require_current_admin_write
from ...models.admin_user import AdminUser
from ...schemas.playback import (
    PlaybackCommandResponse,
    PlaybackPlayRequest,
    PlaybackStopRequest,
)
from ...services.playback_service import PlaybackService


router = APIRouter(prefix="/playback", tags=["playback"])


@router.post("/play", response_model=PlaybackCommandResponse)
async def play(
    payload: PlaybackPlayRequest,
    current_admin: AdminUser = Depends(require_current_admin_write),
    playback_service: PlaybackService = Depends(get_playback_service),
) -> PlaybackCommandResponse:
    return await playback_service.dispatch_play(
        payload.spot_id,
        payload.node_ids,
        replace_if_playing=payload.replace_if_playing,
        origin="admin",
        actor_id=current_admin.username,
    )


@router.post("/stop", response_model=PlaybackCommandResponse)
async def stop(
    payload: PlaybackStopRequest,
    current_admin: AdminUser = Depends(require_current_admin_write),
    playback_service: PlaybackService = Depends(get_playback_service),
) -> PlaybackCommandResponse:
    return await playback_service.dispatch_stop(
        payload.node_ids,
        origin="admin",
        actor_id=current_admin.username,
    )
