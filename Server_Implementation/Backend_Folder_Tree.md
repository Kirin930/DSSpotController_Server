# Backend Folder Tree — Distributed Spot Controller

## Recommended repository structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── health.py
│   │   │   ├── nodes.py
│   │   │   ├── spots.py
│   │   │   ├── playback.py
│   │   │   ├── scheduler.py
│   │   │   └── events.py
│   │   └── deps.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   └── constants.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── migrations/
│   │
│   ├── models/
│   │   ├── node.py
│   │   ├── spot.py
│   │   ├── scheduler.py
│   │   ├── event_log.py
│   │   └── admin_user.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── node.py
│   │   ├── spot.py
│   │   ├── playback.py
│   │   ├── scheduler.py
│   │   ├── event.py
│   │   └── websocket.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── node_service.py
│   │   ├── spot_service.py
│   │   ├── playback_service.py
│   │   ├── scheduler_service.py
│   │   ├── event_service.py
│   │   └── storage_service.py
│   │
│   ├── websocket/
│   │   ├── endpoint.py
│   │   ├── manager.py
│   │   ├── handlers.py
│   │   ├── protocol.py
│   │   └── auth.py
│   │
│   ├── utils/
│   │   ├── time.py
│   │   ├── checksum.py
│   │   ├── file_ops.py
│   │   └── enums.py
│   │
│   └── main.py
│
├── storage/
│   └── spots/
│
├── tests/
│   ├── api/
│   │   ├── test_health.py
│   │   ├── test_nodes.py
│   │   ├── test_spots.py
│   │   ├── test_playback.py
│   │   └── test_scheduler.py
│   ├── websocket/
│   │   ├── test_hello.py
│   │   ├── test_heartbeat.py
│   │   ├── test_sync.py
│   │   └── test_playback_messages.py
│   └── conftest.py
│
├── scripts/
│   ├── seed_admin.py
│   ├── dev_run.sh
│   └── create_node_token.py
│
├── .env
├── .env.example
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Folder responsibilities

## `app/api/routes/`
Contains the REST endpoints used by the admin dashboard and setup flows.

- `auth.py` — login and auth-related routes
- `health.py` — healthcheck endpoints
- `nodes.py` — node listing, toggles, details
- `spots.py` — upload, list, metadata, download
- `playback.py` — manual play/stop commands
- `scheduler.py` — autoplay config and control
- `events.py` — recent logs and playback history

## `app/core/`
Core application config and cross-cutting concerns.

- `config.py` — environment settings
- `security.py` — auth helpers, token checks
- `logging.py` — structured logging config
- `constants.py` — shared constants

## `app/db/`
Database setup.

- `base.py` — model imports for migrations
- `session.py` — SQLAlchemy session creation
- `migrations/` — Alembic migration files

## `app/models/`
SQLAlchemy models representing persisted entities.

## `app/schemas/`
Pydantic request/response models and DTOs.

## `app/services/`
Business logic layer. This should hold most orchestration logic rather than putting it directly inside routes.

## `app/websocket/`
Everything related to node WebSocket communication.

- `endpoint.py` — WebSocket route
- `manager.py` — active connections registry
- `handlers.py` — incoming message dispatch
- `protocol.py` — protocol validation / helpers
- `auth.py` — node authentication during handshake / hello

## `app/utils/`
Small reusable helpers.

## `storage/spots/`
Local audio storage for v1.

## `tests/`
API and WebSocket tests. Keeping them split is useful because the behavior is different.

---

## Suggested implementation order

1. `core/config.py`
2. `db/session.py`
3. `models/node.py`
4. `schemas/websocket.py`
5. `websocket/endpoint.py`
6. `websocket/manager.py`
7. `services/node_service.py`
8. `api/routes/nodes.py`
9. `models/spot.py`
10. `api/routes/spots.py`
11. `services/playback_service.py`
12. `api/routes/playback.py`
13. `scheduler_service.py`
