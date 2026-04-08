from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from .api.routes import auth, events, health, nodes, playback, scheduler, spots
from .core.config import Settings
from .core.logging import configure_logging
from .db.migration_runner import run_migrations
from .db.session import build_engine, build_session_factory
from .services.auth_service import AuthService
from .services.enrollment_service import EnrollmentService
from .services.event_service import EventService
from .services.node_service import NodeService
from .services.playback_service import PlaybackService
from .services.retention_service import RetentionService
from .services.scheduler_service import SchedulerService
from .services.spot_service import SpotService
from .utils.file_ops import ensure_directory
from .websocket.endpoint import router as websocket_router
from .websocket.manager import ConnectionManager


logger = logging.getLogger(__name__)


def _ensure_runtime_paths(settings: Settings) -> None:
    ensure_directory(settings.storage_root)
    ensure_directory(settings.spot_storage_path)
    if settings.database_url.startswith("sqlite:///"):
        database_path = Path(settings.database_url.removeprefix("sqlite:///"))
        ensure_directory(database_path.parent)


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    resolved_settings = settings or Settings.from_env()
    _ensure_runtime_paths(resolved_settings)

    engine = build_engine(resolved_settings)
    session_factory = build_session_factory(engine)
    connection_manager = ConnectionManager()
    event_service = EventService()
    auth_service = AuthService(resolved_settings, event_service)
    node_service = NodeService(resolved_settings, event_service)
    enrollment_service = EnrollmentService(resolved_settings, event_service, node_service)
    spot_service = SpotService(resolved_settings, event_service)
    retention_service = RetentionService(resolved_settings)
    playback_service = PlaybackService(
        resolved_settings,
        session_factory,
        connection_manager,
        spot_service,
        event_service,
    )
    scheduler_service = SchedulerService(
        resolved_settings,
        session_factory,
        playback_service,
        node_service,
        event_service,
        retention_service,
    )
    playback_service.set_scheduler_service(scheduler_service)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        run_migrations(resolved_settings)
        with session_factory() as db:
            auth_service.ensure_default_admin(db)
            node_service.reset_runtime_state(db)
            scheduler_service.ensure_config(db)
        scheduler_service.start_runtime()
        await scheduler_service.initialize()
        logger.info("Server runtime initialized")
        try:
            yield
        finally:
            scheduler_service.shutdown()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.connection_manager = connection_manager
    app.state.event_service = event_service
    app.state.auth_service = auth_service
    app.state.node_service = node_service
    app.state.enrollment_service = enrollment_service
    app.state.spot_service = spot_service
    app.state.retention_service = retention_service
    app.state.playback_service = playback_service
    app.state.scheduler_service = scheduler_service

    app.include_router(health.router, prefix=resolved_settings.api_prefix)
    app.include_router(auth.router, prefix=resolved_settings.api_prefix)
    app.include_router(nodes.router, prefix=resolved_settings.api_prefix)
    app.include_router(spots.router, prefix=resolved_settings.api_prefix)
    app.include_router(playback.router, prefix=resolved_settings.api_prefix)
    app.include_router(scheduler.router, prefix=resolved_settings.api_prefix)
    app.include_router(events.router, prefix=resolved_settings.api_prefix)
    app.include_router(websocket_router)
    return app


app = create_app()
