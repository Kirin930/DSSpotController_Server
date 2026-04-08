# Backend MVP

This is the FastAPI backend for the Distributed Spot Controller server MVP.

## What is implemented

- Alembic-backed schema migrations for SQLite and PostgreSQL workflows
- `GET /api/health`
- `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/auth/csrf`, `POST /api/auth/logout`
- node provisioning plus node list/detail/toggle/sync APIs
- pending enrollment request plus admin approve/reject flow
- spot upload, listing, metadata update, and signed downloads
- manual `play` and `stop` command dispatch with per-node acknowledgements
- autoplay scheduler config plus start/stop controls
- event history API
- node WebSocket endpoint at `/ws/nodes`
- retention cleanup for old event history and inactive spot files

## Local run

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optionally copy `.env.example` to `.env` and adjust values.
4. Apply database migrations:

```bash
python scripts/run_migrations.py
```

5. Start the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The default development database is SQLite at `backend/data/server.db`.

## Default admin

The server bootstraps one admin on first startup using:

- username: `admin`
- password: `admin123!`

Override with `DEFAULT_ADMIN_USERNAME` and `DEFAULT_ADMIN_PASSWORD`.

## CSRF

Cookie-session admin writes now require a CSRF token header.

- `POST /api/auth/login` returns `csrfToken` and sets a matching CSRF cookie
- state-changing admin routes require `X-CSRF-Token`
- bearer-token requests are exempt because they are not cookie-based

## Node provisioning

For the current MVP, nodes are provisioned server-side before they connect.

Two options:

- call `POST /api/nodes/provision` as an authenticated admin
- run the helper script:

```bash
python scripts/create_node_token.py --node-id node-001 --display-name "Entrance Speaker"
```

The returned token is what the Android node sends as `authToken` inside `HELLO`.

## Node enrollment / pairing

The server now supports a pending enrollment flow for brand-new nodes:

1. Node requests enrollment with `POST /api/nodes/enrollments/request`
2. Admin lists pending requests with `GET /api/nodes/enrollments`
3. Admin approves or rejects the request
4. Node polls `GET /api/nodes/enrollments/{id}/status?pairing_code=...`
5. On approval, the node receives its permanent `authToken`

Manual provisioning still exists as an admin override for recovery and token rotation.

## Useful scripts

```bash
python scripts/seed_admin.py --username admin --password new-password
python scripts/create_node_token.py --node-id node-001 --display-name "Entrance Speaker"
python scripts/run_migrations.py
python scripts/validate_postgresql_schema.py
./scripts/dev_run.sh
```

## Notes

- The runtime is intentionally single-process for v1 so the scheduler remains authoritative.
- Admin auth uses signed cookie sessions, but the backend also accepts the same token as a bearer token.
- Cookie-session writes are protected by CSRF validation.
- Node file downloads are protected with short-lived signed URLs bound to `nodeId` and `spotId`.
- WebSocket protocol compatibility now requires the same major version and tolerates minor additions within that major line.
- SQLite is the default for local development and tests. Production can switch to PostgreSQL by setting `DATABASE_URL`.

## Deployment docs

- [Deployment Runbook](./docs/DEPLOYMENT_RUNBOOK.md)
- [Backup And Restore](./docs/BACKUP_AND_RESTORE.md)
- [UAT Checklist](./docs/UAT_CHECKLIST.md)
- [systemd Unit](./deploy/systemd/dsspot-controller.service)
- [logrotate Snippet](./deploy/logrotate/dsspot-controller)
