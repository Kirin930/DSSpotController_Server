from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.db.migration_runner import run_migrations  # noqa: E402
from app.main import create_app  # noqa: E402
from app.schemas.node import NodeProvisionRequest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision a node and print its token.")
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--disabled", action="store_true")
    parser.add_argument("--exclude-from-autoplay", action="store_true")
    parser.add_argument(
        "--actor-id",
        default="script:create_node_token",
        help="Audit actor identifier",
    )
    args = parser.parse_args()

    app = create_app()
    run_migrations(app.state.settings)

    request = NodeProvisionRequest(
        node_id=args.node_id,
        display_name=args.display_name,
        enabled=not args.disabled,
        autoplay_selected=not args.exclude_from_autoplay,
    )
    with app.state.session_factory() as db:
        node, token = app.state.node_service.provision_node(
            db, request, actor_id=args.actor_id
        )

    print(f"nodeId={node.id}")
    print(f"displayName={node.display_name}")
    print(f"enabled={str(node.enabled).lower()}")
    print(f"autoplaySelected={str(node.autoplay_selected).lower()}")
    print(f"authToken={token}")


if __name__ == "__main__":
    main()
