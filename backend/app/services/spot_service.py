from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.security import build_download_signature, verify_download_signature
from ..models.spot import Spot
from ..schemas.spot import SpotUpdateRequest
from ..schemas.websocket import SyncRequiredPayload, SyncSpotPayload
from ..utils.checksum import sha256_bytes
from ..utils.file_ops import ensure_directory, sanitize_filename
from .event_service import EventService


class SpotService:
    def __init__(self, settings: Settings, event_service: EventService) -> None:
        self.settings = settings
        self.event_service = event_service

    def list_spots(self, db: Session) -> list[Spot]:
        return list(db.scalars(select(Spot).order_by(Spot.created_at.desc())))

    def get_spot(self, db: Session, spot_id: str) -> Spot:
        spot = db.get(Spot, spot_id)
        if spot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown spot {spot_id}",
            )
        return spot

    def _validate_upload(self, original_filename: str, content_type: str | None) -> None:
        suffix = Path(original_filename or "").suffix.lower()
        if suffix not in self.settings.allowed_upload_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported audio extension",
            )

        if content_type and content_type not in self.settings.allowed_upload_mime_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported audio MIME type",
            )

    def create_spot(
        self,
        db: Session,
        *,
        title: str,
        content: bytes,
        original_filename: str,
        content_type: str | None,
        actor_id: str,
    ) -> Spot:
        self._validate_upload(original_filename, content_type)
        safe_filename = sanitize_filename(original_filename)
        spot = Spot(
            title=title,
            filename=safe_filename,
            original_filename=original_filename,
            mime_type=content_type or "application/octet-stream",
            checksum=sha256_bytes(content),
            active=True,
            storage_path="",
        )
        db.add(spot)
        db.flush()

        ensure_directory(self.settings.spot_storage_path)
        final_path = self.settings.spot_storage_path / f"{spot.id}_{safe_filename}"
        final_path.write_bytes(content)
        spot.storage_path = str(final_path.resolve())

        self.event_service.log(
            db,
            "SPOT_UPLOADED",
            details=f"Uploaded spot {spot.title}",
            spot_id=spot.id,
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(spot)
        return spot

    def update_spot(
        self, db: Session, spot_id: str, payload: SpotUpdateRequest, *, actor_id: str
    ) -> Spot:
        spot = self.get_spot(db, spot_id)
        if payload.title is not None:
            spot.title = payload.title
        if payload.active is not None:
            spot.active = payload.active

        self.event_service.log(
            db,
            "SPOT_UPDATED",
            details=f"Updated spot {spot.id}",
            spot_id=spot.id,
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(spot)
        return spot

    def build_signed_download_url(self, spot: Spot, node_id: str) -> str:
        expires = int(time.time()) + self.settings.signed_download_ttl_seconds
        signature = build_download_signature(
            self.settings.secret_key, node_id, spot.id, expires
        )
        query = urlencode(
            {
                "nodeId": node_id,
                "expires": expires,
                "signature": signature,
            }
        )
        return (
            f"{self.settings.public_base_url.rstrip('/')}"
            f"{self.settings.api_prefix}/spots/{spot.id}/download?{query}"
        )

    def build_sync_payload(self, db: Session, node_id: str) -> SyncRequiredPayload:
        spots = list(
            db.scalars(
                select(Spot).where(Spot.active.is_(True)).order_by(Spot.created_at.asc())
            )
        )
        sync_spots = [
            SyncSpotPayload(
                spot_id=spot.id,
                title=spot.title,
                version=spot.version,
                checksum=spot.checksum,
                download_url=self.build_signed_download_url(spot, node_id),
            )
            for spot in spots
        ]
        return SyncRequiredPayload(spots=sync_spots)

    def verify_download_access(
        self,
        db: Session,
        *,
        spot_id: str,
        node_id: str,
        expires: int,
        signature: str,
    ) -> Spot:
        spot = self.get_spot(db, spot_id)
        is_valid = verify_download_signature(
            self.settings.secret_key,
            node_id,
            spot_id,
            expires,
            signature,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired signed download URL",
            )
        return spot
