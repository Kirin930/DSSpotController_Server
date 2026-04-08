from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from ..core.config import Settings


def build_alembic_config(settings: Settings) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option(
        "script_location", str((backend_root / "app" / "db" / "migrations").resolve())
    )
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def run_migrations(settings: Settings) -> None:
    command.upgrade(build_alembic_config(settings), "head")
