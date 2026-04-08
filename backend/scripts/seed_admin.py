from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import hash_secret  # noqa: E402
from app.db.migration_runner import run_migrations  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.admin_user import AdminUser  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an admin user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    app = create_app()
    run_migrations(app.state.settings)

    with app.state.session_factory() as db:
        admin_user = db.scalar(
            select(AdminUser).where(AdminUser.username == args.username)
        )
        if admin_user is None:
            admin_user = AdminUser(
                username=args.username,
                password_hash=hash_secret(args.password),
            )
            db.add(admin_user)
        else:
            admin_user.password_hash = hash_secret(args.password)

        db.commit()
        print(f"Admin user ready: {args.username}")


if __name__ == "__main__":
    main()
