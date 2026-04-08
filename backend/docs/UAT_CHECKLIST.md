# UAT Checklist

## Authentication

- Login works with the configured admin account.
- `GET /api/auth/me` returns the current admin profile.
- Cookie-session write requests fail without `X-CSRF-Token`.
- Cookie-session write requests succeed with the issued CSRF token.

## Spot management

- Upload a valid audio file and confirm it appears in `GET /api/spots`.
- Toggle a spot inactive and confirm it no longer appears in sync payloads.
- Download the spot as an authenticated admin.

## Enrollment / provisioning

- Create a pending enrollment request.
- Confirm the request appears in `GET /api/nodes/enrollments?status=pending`.
- Approve the request and confirm the node can retrieve its `authToken`.
- Reject a request and confirm the rejection reason is visible to the node.

## Node sync

- Connect a node over WebSocket and send `HELLO`.
- Confirm the server replies with `REGISTER_ACK`.
- Confirm `SYNC_REQUIRED` includes signed URLs with `nodeId`, `expires`, and `signature`.
- Confirm the node can report `SYNC_RESULT` and the event log updates.

## Manual playback

- Trigger `POST /api/playback/play` for one node.
- Confirm the node receives `PLAY`.
- Confirm the API waits for `PLAYBACK_STARTED` and returns per-node results.
- Trigger `POST /api/playback/stop` and confirm `PLAYBACK_STOPPED`.

## Scheduler

- Configure a spot sequence and interval.
- Start autoplay and confirm the next run is scheduled.
- Verify the current spot advances correctly across ticks.
- Trigger a manual play while autoplay is enabled and confirm the scheduler timer resets.

## Recovery

- Disconnect a node and confirm it eventually becomes `stale` and then `offline`.
- Reconnect the node and confirm fresh status rebuilds the live view.
- Restart the backend and confirm migrations run, scheduler state reloads, and nodes can reconnect cleanly.

## Operations

- Validate the `systemd` service starts on boot and restarts after a forced crash.
- Verify manual backup commands succeed for DB and spot storage.
- Confirm log rotation is configured on the target host.
