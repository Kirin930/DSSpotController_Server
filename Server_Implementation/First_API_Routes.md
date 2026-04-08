# First API Routes — Distributed Spot Controller Backend

## Goal

These are the recommended first REST routes for the backend MVP. They cover:
- health
- auth
- node listing and control
- spot upload and listing
- manual playback
- scheduler control
- event visibility

The WebSocket channel is still required for node realtime communication. These routes are for the admin dashboard and file transfer.

---

# 1. Health Routes

## `GET /api/health`
Basic server healthcheck.

### Response
```json
{
  "status": "ok"
}
```

---

# 2. Auth Routes

## `POST /api/auth/login`
Admin login.

### Request
```json
{
  "username": "admin",
  "password": "secret"
}
```

### Response
```json
{
  "accessToken": "jwt-or-session-token",
  "tokenType": "bearer"
}
```

---

## `GET /api/auth/me`
Returns current admin profile.

### Response
```json
{
  "id": "admin-1",
  "username": "admin"
}
```

---

# 3. Node Routes

## `GET /api/nodes`
Returns all known nodes with current live status snapshot.

### Response
```json
[
  {
    "id": "node-001",
    "displayName": "Entrance Speaker",
    "enabled": true,
    "autoplaySelected": true,
    "connectionState": "online",
    "operationalState": "ready",
    "currentSpotId": null,
    "lastSeenAt": "2026-03-18T19:00:00Z"
  }
]
```

---

## `GET /api/nodes/{node_id}`
Returns one node detail.

### Response
```json
{
  "id": "node-001",
  "displayName": "Entrance Speaker",
  "enabled": true,
  "autoplaySelected": true,
  "connectionState": "online",
  "operationalState": "ready",
  "currentSpotId": null,
  "lastSeenAt": "2026-03-18T19:00:00Z",
  "appVersion": "1.0.0",
  "platform": "android"
}
```

---

## `PATCH /api/nodes/{node_id}/enabled`
Enable or disable a node.

### Request
```json
{
  "enabled": false
}
```

### Response
```json
{
  "id": "node-001",
  "enabled": false
}
```

---

## `PATCH /api/nodes/{node_id}/autoplay`
Include or exclude a node from autoplay.

### Request
```json
{
  "autoplaySelected": true
}
```

### Response
```json
{
  "id": "node-001",
  "autoplaySelected": true
}
```

---

## `POST /api/nodes/{node_id}/sync`
Manually request a sync for one node.

### Response
```json
{
  "message": "Sync requested",
  "nodeId": "node-001"
}
```

---

# 4. Spot Routes

## `GET /api/spots`
Returns all spots in library.

### Response
```json
[
  {
    "id": "spot-001",
    "title": "Spring Promo",
    "filename": "spring_promo.mp3",
    "version": 1,
    "checksum": "sha256:abc123",
    "active": true
  }
]
```

---

## `POST /api/spots`
Uploads a new spot.

### Request
Multipart form-data:
- `file`
- `title`

### Response
```json
{
  "id": "spot-001",
  "title": "Spring Promo",
  "filename": "spring_promo.mp3",
  "version": 1,
  "checksum": "sha256:abc123",
  "active": true
}
```

---

## `GET /api/spots/{spot_id}`
Returns spot metadata.

### Response
```json
{
  "id": "spot-001",
  "title": "Spring Promo",
  "filename": "spring_promo.mp3",
  "version": 1,
  "checksum": "sha256:abc123",
  "active": true
}
```

---

## `PATCH /api/spots/{spot_id}`
Updates spot metadata such as title or active status.

### Request
```json
{
  "title": "Spring Promo Updated",
  "active": true
}
```

---

## `GET /api/spots/{spot_id}/download`
Authenticated endpoint used by nodes to download the actual audio file.

### Response
Binary file stream

---

# 5. Playback Routes

## `POST /api/playback/play`
Manually trigger playback of one spot on one or more nodes.

### Request
```json
{
  "spotId": "spot-001",
  "nodeIds": ["node-001", "node-002"],
  "replaceIfPlaying": true
}
```

### Response
```json
{
  "message": "Play command dispatched",
  "spotId": "spot-001",
  "nodeIds": ["node-001", "node-002"]
}
```

---

## `POST /api/playback/stop`
Stop playback on one or more nodes.

### Request
```json
{
  "nodeIds": ["node-001", "node-002"]
}
```

### Response
```json
{
  "message": "Stop command dispatched",
  "nodeIds": ["node-001", "node-002"]
}
```

---

# 6. Scheduler Routes

## `GET /api/scheduler`
Returns current autoplay config.

### Response
```json
{
  "enabled": false,
  "intervalMinutes": 15,
  "currentIndex": 0,
  "spotSequence": ["spot-001", "spot-002", "spot-003"]
}
```

---

## `PUT /api/scheduler`
Creates or replaces autoplay config.

### Request
```json
{
  "enabled": false,
  "intervalMinutes": 15,
  "spotSequence": ["spot-001", "spot-002", "spot-003"]
}
```

### Response
```json
{
  "enabled": false,
  "intervalMinutes": 15,
  "currentIndex": 0,
  "spotSequence": ["spot-001", "spot-002", "spot-003"]
}
```

---

## `POST /api/scheduler/start`
Starts autoplay.

### Response
```json
{
  "message": "Autoplay started"
}
```

---

## `POST /api/scheduler/stop`
Stops autoplay.

### Response
```json
{
  "message": "Autoplay stopped"
}
```

---

# 7. Event Routes

## `GET /api/events`
Returns recent operational events.

### Example query params
- `limit=50`
- `nodeId=node-001`

### Response
```json
[
  {
    "id": "evt-001",
    "eventType": "PLAYBACK_STARTED",
    "nodeId": "node-001",
    "spotId": "spot-001",
    "createdAt": "2026-03-18T19:00:00Z",
    "details": "Playback started"
  }
]
```

---

# 8. First routes to implement in order

1. `GET /api/health`
2. `POST /api/auth/login`
3. `GET /api/nodes`
4. `PATCH /api/nodes/{node_id}/enabled`
5. `GET /api/spots`
6. `POST /api/spots`
7. `GET /api/spots/{spot_id}/download`
8. `POST /api/playback/play`
9. `POST /api/playback/stop`
10. `GET /api/scheduler`
11. `PUT /api/scheduler`
12. `POST /api/scheduler/start`
13. `POST /api/scheduler/stop`
14. `GET /api/events`

---

# 9. Notes

- Node registration itself should happen via WebSocket, not via REST.
- File download should stay on HTTP, not on WebSocket.
- In v1, these routes are enough to support the first admin dashboard.
