from __future__ import annotations

import asyncio
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import Settings
from ..models.scheduler import SchedulerConfig
from ..models.spot import Spot
from ..schemas.scheduler import SchedulerConfigResponse, SchedulerConfigUpdate
from ..utils.time import utc_now
from .event_service import EventService
from .node_service import NodeService
from .playback_service import PlaybackService
from .retention_service import RetentionService


AUTOPLAY_JOB_ID = "autoplay-next-run"
HEARTBEAT_SWEEP_JOB_ID = "heartbeat-sweep"
RETENTION_SWEEP_JOB_ID = "retention-sweep"


class SchedulerService:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        playback_service: PlaybackService,
        node_service: NodeService,
        event_service: EventService,
        retention_service: RetentionService,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.playback_service = playback_service
        self.node_service = node_service
        self.event_service = event_service
        self.retention_service = retention_service
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self._tick_lock = asyncio.Lock()

    def start_runtime(self) -> None:
        if not self.scheduler.running:
            self.scheduler.add_job(
                self._sweep_liveness,
                IntervalTrigger(
                    seconds=self.settings.heartbeat_sweep_interval_seconds
                ),
                id=HEARTBEAT_SWEEP_JOB_ID,
                replace_existing=True,
            )
            self.scheduler.add_job(
                self._retention_sweep,
                IntervalTrigger(hours=self.settings.retention_sweep_interval_hours),
                id=RETENTION_SWEEP_JOB_ID,
                replace_existing=True,
            )
            self.scheduler.start()

    async def initialize(self) -> None:
        with self.session_factory() as db:
            config = self.ensure_config(db)
            if config.enabled:
                next_run_at = config.next_run_at or (
                    utc_now() + timedelta(minutes=config.interval_minutes)
                )
                config.next_run_at = next_run_at
                db.commit()
                self._schedule_next_run(next_run_at)

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def ensure_config(self, db: Session) -> SchedulerConfig:
        config = db.get(SchedulerConfig, 1)
        if config is None:
            config = SchedulerConfig(
                id=1,
                enabled=False,
                interval_minutes=self.settings.scheduler_default_interval_minutes,
                current_index=0,
                revision=0,
                spot_sequence=[],
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        return config

    def get_config(self, db: Session) -> SchedulerConfig:
        return self.ensure_config(db)

    async def update_config(
        self, db: Session, payload: SchedulerConfigUpdate, *, actor_id: str
    ) -> SchedulerConfig:
        config = self.ensure_config(db)
        if (
            payload.expected_revision is not None
            and payload.expected_revision != config.revision
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Scheduler config revision mismatch",
            )

        missing_spot_ids = self._find_missing_spot_ids(db, payload.spot_sequence)
        if missing_spot_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown spot IDs: {', '.join(missing_spot_ids)}",
            )

        config.interval_minutes = payload.interval_minutes
        config.spot_sequence = payload.spot_sequence
        config.enabled = payload.enabled
        config.revision += 1
        config.next_run_at = (
            utc_now() + timedelta(minutes=config.interval_minutes)
            if config.enabled
            else None
        )
        self.event_service.log(
            db,
            "SCHEDULER_CONFIG_UPDATED",
            details=(
                f"Scheduler config updated; enabled={config.enabled}, "
                f"intervalMinutes={config.interval_minutes}"
            ),
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(config)

        if config.enabled and config.next_run_at is not None:
            self._schedule_next_run(config.next_run_at)
        else:
            self._remove_autoplay_job()
        return config

    async def start_autoplay(self, db: Session, *, actor_id: str) -> SchedulerConfig:
        config = self.ensure_config(db)
        config.enabled = True
        config.next_run_at = utc_now() + timedelta(minutes=config.interval_minutes)
        self.event_service.log(
            db,
            "SCHEDULER_STARTED",
            details="Autoplay started",
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(config)
        self._schedule_next_run(config.next_run_at)
        return config

    async def stop_autoplay(self, db: Session, *, actor_id: str) -> SchedulerConfig:
        config = self.ensure_config(db)
        config.enabled = False
        config.next_run_at = None
        self.event_service.log(
            db,
            "SCHEDULER_STOPPED",
            details="Autoplay stopped",
            actor_type="admin",
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(config)
        self._remove_autoplay_job()
        return config

    async def reset_after_manual_play(self, *, actor_id: str) -> None:
        with self.session_factory() as db:
            config = self.ensure_config(db)
            if not config.enabled:
                return
            config.next_run_at = utc_now() + timedelta(minutes=config.interval_minutes)
            self.event_service.log(
                db,
                "SCHEDULER_RESET_AFTER_MANUAL_PLAY",
                details="Autoplay timer reset after manual play",
                actor_type="admin",
                actor_id=actor_id,
            )
            db.commit()
            self._schedule_next_run(config.next_run_at)

    def to_response(self, config: SchedulerConfig) -> SchedulerConfigResponse:
        return SchedulerConfigResponse.model_validate(config)

    def _find_missing_spot_ids(self, db: Session, spot_ids: list[str]) -> list[str]:
        if not spot_ids:
            return []
        existing_ids = {
            spot_id
            for spot_id in db.scalars(select(Spot.id).where(Spot.id.in_(spot_ids)))
        }
        return [spot_id for spot_id in spot_ids if spot_id not in existing_ids]

    def _schedule_next_run(self, run_at) -> None:
        self.scheduler.add_job(
            self._autoplay_tick,
            trigger=DateTrigger(run_date=run_at),
            id=AUTOPLAY_JOB_ID,
            replace_existing=True,
            misfire_grace_time=30,
        )

    def _remove_autoplay_job(self) -> None:
        try:
            self.scheduler.remove_job(AUTOPLAY_JOB_ID)
        except Exception:
            pass

    def _sweep_liveness(self) -> None:
        with self.session_factory() as db:
            self.node_service.sweep_liveness(db)

    def _retention_sweep(self) -> None:
        with self.session_factory() as db:
            result = self.retention_service.sweep(db)
            if result.deleted_event_count or result.deleted_spot_count:
                self.event_service.log(
                    db,
                    "RETENTION_SWEEP_COMPLETED",
                    details=(
                        "Retention cleanup completed; "
                        f"deletedEvents={result.deleted_event_count}, "
                        f"deletedSpots={result.deleted_spot_count}"
                    ),
                    actor_type="system",
                    actor_id="retention-sweep",
                )
                db.commit()

    async def _autoplay_tick(self) -> None:
        if self._tick_lock.locked():
            return

        async with self._tick_lock:
            with self.session_factory() as db:
                config = self.ensure_config(db)
                if not config.enabled:
                    return

                active_sequence = self._active_sequence(db, config.spot_sequence)
                if not active_sequence:
                    self.event_service.log(
                        db,
                        "SCHEDULER_SKIPPED",
                        details="Autoplay skipped because the active sequence is empty",
                        actor_type="system",
                        actor_id="scheduler",
                    )
                    config.next_run_at = utc_now() + timedelta(
                        minutes=config.interval_minutes
                    )
                    db.commit()
                    self._schedule_next_run(config.next_run_at)
                    return

                current_index = config.current_index % len(active_sequence)
                spot_id = active_sequence[current_index]
                target_node_ids = self.node_service.get_autoplay_target_node_ids(db)

            await self.playback_service.dispatch_play(
                spot_id,
                target_node_ids,
                replace_if_playing=True,
                origin="scheduler",
                actor_id="scheduler",
                request_prefix="autoplay",
                reset_scheduler=False,
            )

            with self.session_factory() as db:
                config = self.ensure_config(db)
                if not config.enabled:
                    return
                active_sequence = self._active_sequence(db, config.spot_sequence)
                if active_sequence:
                    config.current_index = (config.current_index + 1) % len(
                        active_sequence
                    )
                config.last_triggered_at = utc_now()
                config.next_run_at = utc_now() + timedelta(
                    minutes=config.interval_minutes
                )
                self.event_service.log(
                    db,
                    "SCHEDULER_TICK",
                    details=f"Autoplay dispatched spot {spot_id}",
                    spot_id=spot_id,
                    actor_type="system",
                    actor_id="scheduler",
                )
                db.commit()
                self._schedule_next_run(config.next_run_at)

    def _active_sequence(self, db: Session, configured_ids: list[str]) -> list[str]:
        if not configured_ids:
            return []
        active_ids = {
            spot_id
            for spot_id in db.scalars(
                select(Spot.id).where(
                    Spot.id.in_(configured_ids), Spot.active.is_(True)
                )
            )
        }
        return [spot_id for spot_id in configured_ids if spot_id in active_ids]
