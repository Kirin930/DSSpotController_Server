from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings  # noqa: E402
from app.db.migration_runner import run_migrations  # noqa: E402
from app.db.session import build_engine  # noqa: E402


EXPECTED_TABLES = {
    "admin_users",
    "nodes",
    "node_enrollments",
    "spots",
    "scheduler_config",
    "event_logs",
}


def main() -> None:
    settings = Settings.from_env(repo_root=BACKEND_ROOT.parent)
    if not settings.database_url.startswith("postgresql"):
        raise SystemExit(
            "DATABASE_URL must point to PostgreSQL for this validation script."
        )

    run_migrations(settings)
    engine = build_engine(settings)
    with engine.connect() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
    missing = sorted(EXPECTED_TABLES - tables)
    if missing:
        raise SystemExit(
            f"PostgreSQL schema validation failed; missing tables: {', '.join(missing)}"
        )
    print("PostgreSQL schema validation passed.")


if __name__ == "__main__":
    main()
