# Distributed Spot Controller Server

This repository now contains the MVP implementation of the Main Web Server described in [`Server_Implementation`](./Server_Implementation).

The runnable backend lives in [`backend`](./backend). It implements:

- admin authentication with signed cookie sessions
- node provisioning and token issuance
- REST APIs for nodes, spots, playback, scheduler, and events
- a node WebSocket gateway for `HELLO`, heartbeats, sync, and playback events
- signed short-lived spot download URLs for nodes
- a single-process server-side autoplay scheduler
- SQLite-by-default local development, with `DATABASE_URL` support for PostgreSQL

Start with [`backend/README.md`](./backend/README.md) for setup and usage.
