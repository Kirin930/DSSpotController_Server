from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    DEFAULT_ALLOWED_UPLOAD_EXTENSIONS,
    DEFAULT_ALLOWED_UPLOAD_MIME_TYPES,
    DEFAULT_COMMAND_ACK_TIMEOUT_SECONDS,
    DEFAULT_CSRF_TTL_SECONDS,
    DEFAULT_ENROLLMENT_CODE_LENGTH,
    DEFAULT_ENROLLMENT_TTL_SECONDS,
    DEFAULT_EVENT_RETENTION_DAYS,
    DEFAULT_HEARTBEAT_OFFLINE_AFTER_SECONDS,
    DEFAULT_HEARTBEAT_STALE_AFTER_SECONDS,
    DEFAULT_HEARTBEAT_SWEEP_INTERVAL_SECONDS,
    DEFAULT_INACTIVE_SPOT_RETENTION_DAYS,
    DEFAULT_LOGIN_LOCKOUT_SECONDS,
    DEFAULT_LOGIN_MAX_ATTEMPTS,
    DEFAULT_LOGIN_WINDOW_SECONDS,
    DEFAULT_RETENTION_SWEEP_INTERVAL_HOURS,
    DEFAULT_SCHEDULER_INTERVAL_MINUTES,
    DEFAULT_SESSION_TTL_SECONDS,
    DEFAULT_SIGNED_DOWNLOAD_TTL_SECONDS,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    PROTOCOL_VERSION,
    PROTOCOL_MINOR_VERSION,
    SESSION_COOKIE_NAME,
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _env_tuple(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None:
        return default
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(values) if values else default


@dataclass(slots=True)
class Settings:
    app_name: str
    api_prefix: str
    websocket_path: str
    secret_key: str
    database_url: str
    storage_root: Path
    public_base_url: str
    protocol_version: int
    protocol_minor_version: int
    session_cookie_name: str
    session_ttl_seconds: int
    session_cookie_secure: bool
    csrf_cookie_name: str
    csrf_header_name: str
    csrf_ttl_seconds: int
    signed_download_ttl_seconds: int
    command_ack_timeout_seconds: int
    heartbeat_sweep_interval_seconds: int
    heartbeat_stale_after_seconds: int
    heartbeat_offline_after_seconds: int
    scheduler_default_interval_minutes: int
    default_admin_username: str
    default_admin_password: str
    login_window_seconds: int
    login_lockout_seconds: int
    login_max_attempts: int
    allowed_upload_extensions: tuple[str, ...]
    allowed_upload_mime_types: tuple[str, ...]
    event_retention_days: int
    inactive_spot_retention_days: int
    retention_sweep_interval_hours: int
    enrollment_code_length: int
    enrollment_ttl_seconds: int

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> "Settings":
        resolved_repo_root = repo_root or Path(__file__).resolve().parents[3]
        backend_root = resolved_repo_root / "backend"
        storage_root = Path(
            os.getenv("DS_STORAGE_ROOT", str((backend_root / "storage").resolve()))
        )
        default_database_path = (backend_root / "data" / "server.db").resolve()
        default_database_url = f"sqlite:///{default_database_path.as_posix()}"

        return cls(
            app_name=os.getenv(
                "APP_NAME", "Distributed Spot Controller Main Web Server"
            ),
            api_prefix=os.getenv("API_PREFIX", "/api"),
            websocket_path=os.getenv("WEBSOCKET_PATH", "/ws/nodes"),
            secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
            database_url=os.getenv("DATABASE_URL", default_database_url),
            storage_root=storage_root,
            public_base_url=os.getenv("PUBLIC_BASE_URL", "http://localhost:8000"),
            protocol_version=_env_int("PROTOCOL_VERSION", PROTOCOL_VERSION),
            protocol_minor_version=_env_int(
                "PROTOCOL_MINOR_VERSION", PROTOCOL_MINOR_VERSION
            ),
            session_cookie_name=os.getenv(
                "SESSION_COOKIE_NAME", SESSION_COOKIE_NAME
            ),
            session_ttl_seconds=_env_int(
                "SESSION_TTL_SECONDS", DEFAULT_SESSION_TTL_SECONDS
            ),
            session_cookie_secure=_env_bool("SESSION_COOKIE_SECURE", False),
            csrf_cookie_name=os.getenv("CSRF_COOKIE_NAME", CSRF_COOKIE_NAME),
            csrf_header_name=os.getenv("CSRF_HEADER_NAME", CSRF_HEADER_NAME),
            csrf_ttl_seconds=_env_int(
                "CSRF_TTL_SECONDS", DEFAULT_CSRF_TTL_SECONDS
            ),
            signed_download_ttl_seconds=_env_int(
                "SIGNED_DOWNLOAD_TTL_SECONDS", DEFAULT_SIGNED_DOWNLOAD_TTL_SECONDS
            ),
            command_ack_timeout_seconds=_env_int(
                "COMMAND_ACK_TIMEOUT_SECONDS", DEFAULT_COMMAND_ACK_TIMEOUT_SECONDS
            ),
            heartbeat_sweep_interval_seconds=_env_int(
                "HEARTBEAT_SWEEP_INTERVAL_SECONDS",
                DEFAULT_HEARTBEAT_SWEEP_INTERVAL_SECONDS,
            ),
            heartbeat_stale_after_seconds=_env_int(
                "HEARTBEAT_STALE_AFTER_SECONDS",
                DEFAULT_HEARTBEAT_STALE_AFTER_SECONDS,
            ),
            heartbeat_offline_after_seconds=_env_int(
                "HEARTBEAT_OFFLINE_AFTER_SECONDS",
                DEFAULT_HEARTBEAT_OFFLINE_AFTER_SECONDS,
            ),
            scheduler_default_interval_minutes=_env_int(
                "SCHEDULER_DEFAULT_INTERVAL_MINUTES",
                DEFAULT_SCHEDULER_INTERVAL_MINUTES,
            ),
            default_admin_username=os.getenv("DEFAULT_ADMIN_USERNAME", "admin"),
            default_admin_password=os.getenv(
                "DEFAULT_ADMIN_PASSWORD", "admin123!"
            ),
            login_window_seconds=_env_int(
                "LOGIN_WINDOW_SECONDS", DEFAULT_LOGIN_WINDOW_SECONDS
            ),
            login_lockout_seconds=_env_int(
                "LOGIN_LOCKOUT_SECONDS", DEFAULT_LOGIN_LOCKOUT_SECONDS
            ),
            login_max_attempts=_env_int(
                "LOGIN_MAX_ATTEMPTS", DEFAULT_LOGIN_MAX_ATTEMPTS
            ),
            allowed_upload_extensions=_env_tuple(
                "ALLOWED_UPLOAD_EXTENSIONS", DEFAULT_ALLOWED_UPLOAD_EXTENSIONS
            ),
            allowed_upload_mime_types=_env_tuple(
                "ALLOWED_UPLOAD_MIME_TYPES", DEFAULT_ALLOWED_UPLOAD_MIME_TYPES
            ),
            event_retention_days=_env_int(
                "EVENT_RETENTION_DAYS", DEFAULT_EVENT_RETENTION_DAYS
            ),
            inactive_spot_retention_days=_env_int(
                "INACTIVE_SPOT_RETENTION_DAYS",
                DEFAULT_INACTIVE_SPOT_RETENTION_DAYS,
            ),
            retention_sweep_interval_hours=_env_int(
                "RETENTION_SWEEP_INTERVAL_HOURS",
                DEFAULT_RETENTION_SWEEP_INTERVAL_HOURS,
            ),
            enrollment_code_length=_env_int(
                "ENROLLMENT_CODE_LENGTH", DEFAULT_ENROLLMENT_CODE_LENGTH
            ),
            enrollment_ttl_seconds=_env_int(
                "ENROLLMENT_TTL_SECONDS", DEFAULT_ENROLLMENT_TTL_SECONDS
            ),
        )

    @property
    def spot_storage_path(self) -> Path:
        return self.storage_root / "spots"
