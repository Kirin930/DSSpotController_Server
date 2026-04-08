from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings  # noqa: E402
from app.db.migration_runner import run_migrations  # noqa: E402


def main() -> None:
    settings = Settings.from_env(repo_root=BACKEND_ROOT.parent)
    run_migrations(settings)
    print("Database migrations applied successfully.")


if __name__ == "__main__":
    main()
