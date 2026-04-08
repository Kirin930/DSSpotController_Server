# First WebSocket Message Models — Distributed Spot Controller

## Goal

These are the first protocol models to implement in code for the MVP.  
They are intentionally limited to the minimum set needed for:
- node registration
- liveness
- sync orchestration
- playback commands
- playback feedback

---

# 1. Common Envelope

Every message should use the same envelope.

```json
{
  "type": "MESSAGE_TYPE",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:00:00Z",
  "requestId": "optional-id",
  "payload": {}
}
```

### Fields
- `type`: message type
- `protocolVersion`: integer, start with `1`
- `timestamp`: ISO-8601 UTC timestamp
- `requestId`: optional correlation ID
- `payload`: message-specific object

---

# 2. First Incoming Models (Node → Server)

## 2.1 HELLO

```json
{
  "type": "HELLO",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:00:00Z",
  "payload": {
    "nodeId": "node-001",
    "authToken": "node-secret-token",
    "displayName": "Entrance Speaker",
    "platform": "android",
    "appVersion": "1.0.0",
    "deviceModel": "Samsung Galaxy A14"
  }
}
```

### Purpose
- identify node
- authenticate node
- provide metadata

---

## 2.2 HEARTBEAT

```json
{
  "type": "HEARTBEAT",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:00:20Z",
  "payload": {
    "nodeId": "node-001",
    "status": "ready",
    "currentSpotId": null
  }
}
```

### Purpose
- confirm liveness
- refresh status snapshot

---

## 2.3 STATUS_UPDATE

```json
{
  "type": "STATUS_UPDATE",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:01:00Z",
  "payload": {
    "nodeId": "node-001",
    "status": "syncing",
    "currentSpotId": null,
    "details": "Downloading 2 spots"
  }
}
```

### Purpose
- send state changes

---

## 2.4 SYNC_RESULT

```json
{
  "type": "SYNC_RESULT",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:02:00Z",
  "requestId": "sync-001",
  "payload": {
    "nodeId": "node-001",
    "result": "success",
    "downloadedSpotIds": ["spot-001", "spot-002"],
    "updatedSpotIds": [],
    "failedSpotIds": []
  }
}
```

### Purpose
- report sync completion outcome

---

## 2.5 PLAYBACK_STARTED

```json
{
  "type": "PLAYBACK_STARTED",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:05:00Z",
  "requestId": "play-145",
  "payload": {
    "nodeId": "node-001",
    "spotId": "spot-001"
  }
}
```

---

## 2.6 PLAYBACK_FINISHED

```json
{
  "type": "PLAYBACK_FINISHED",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:05:24Z",
  "requestId": "play-145",
  "payload": {
    "nodeId": "node-001",
    "spotId": "spot-001",
    "durationMs": 24000
  }
}
```

---

## 2.7 PLAYBACK_STOPPED

```json
{
  "type": "PLAYBACK_STOPPED",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:05:10Z",
  "requestId": "stop-200",
  "payload": {
    "nodeId": "node-001",
    "spotId": "spot-001",
    "reason": "server_stop_command"
  }
}
```

---

## 2.8 PLAYBACK_ERROR

```json
{
  "type": "PLAYBACK_ERROR",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:05:02Z",
  "requestId": "play-145",
  "payload": {
    "nodeId": "node-001",
    "spotId": "spot-001",
    "errorCode": "FILE_NOT_FOUND",
    "errorMessage": "Local audio file is missing"
  }
}
```

---

# 3. First Outgoing Models (Server → Node)

## 3.1 REGISTER_ACK

```json
{
  "type": "REGISTER_ACK",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:00:01Z",
  "payload": {
    "nodeId": "node-001",
    "enabled": true,
    "autoplaySelected": true,
    "syncRequired": true
  }
}
```

### Purpose
- confirm successful registration
- send initial config snapshot

---

## 3.2 SYNC_REQUIRED

```json
{
  "type": "SYNC_REQUIRED",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:01:30Z",
  "requestId": "sync-001",
  "payload": {
    "spots": [
      {
        "spotId": "spot-001",
        "title": "Spring Promo",
        "version": 2,
        "checksum": "sha256:abc123",
        "downloadUrl": "https://server.local/api/spots/spot-001/download"
      },
      {
        "spotId": "spot-002",
        "title": "Weekend Offer",
        "version": 1,
        "checksum": "sha256:def456",
        "downloadUrl": "https://server.local/api/spots/spot-002/download"
      }
    ]
  }
}
```

### Purpose
- tell node which local files it must have

---

## 3.3 PLAY

```json
{
  "type": "PLAY",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:05:00Z",
  "requestId": "play-145",
  "payload": {
    "spotId": "spot-001",
    "replaceIfPlaying": true
  }
}
```

### Purpose
- trigger immediate playback

---

## 3.4 STOP

```json
{
  "type": "STOP",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:05:10Z",
  "requestId": "stop-200",
  "payload": {}
}
```

### Purpose
- stop current playback

---

## 3.5 SET_ENABLED

```json
{
  "type": "SET_ENABLED",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:10:00Z",
  "payload": {
    "enabled": false
  }
}
```

### Purpose
- enable or disable node execution

---

## 3.6 ERROR

```json
{
  "type": "ERROR",
  "protocolVersion": 1,
  "timestamp": "2026-03-18T20:11:00Z",
  "requestId": "play-145",
  "payload": {
    "errorCode": "UNKNOWN_SPOT",
    "errorMessage": "Spot does not exist"
  }
}
```

---

# 4. Suggested Kotlin sealed model structure

```kotlin
sealed interface WsMessage {
    val type: String
    val protocolVersion: Int
    val timestamp: String
    val requestId: String?
}
```

### Node → Server payload models
- `HelloPayload`
- `HeartbeatPayload`
- `StatusUpdatePayload`
- `SyncResultPayload`
- `PlaybackStartedPayload`
- `PlaybackFinishedPayload`
- `PlaybackStoppedPayload`
- `PlaybackErrorPayload`

### Server → Node payload models
- `RegisterAckPayload`
- `SyncRequiredPayload`
- `PlayPayload`
- `StopPayload`
- `SetEnabledPayload`
- `ErrorPayload`

---

# 5. Suggested Python Pydantic model structure

```python
from pydantic import BaseModel
from typing import Optional

class WsEnvelope(BaseModel):
    type: str
    protocolVersion: int = 1
    timestamp: str
    requestId: Optional[str] = None
    payload: dict
```

Then create one payload model per message type and validate by `type`.

---

# 6. First statuses and enums to define

## Node statuses
- `offline`
- `online`
- `idle`
- `syncing`
- `ready`
- `playing`
- `stopped`
- `error`

## Playback error codes
- `FILE_NOT_FOUND`
- `FILE_CORRUPTED`
- `PLAYBACK_ENGINE_FAILURE`
- `NODE_DISABLED`
- `INVALID_MESSAGE`
- `UNAUTHORIZED`

---

# 7. First message models to implement in order

1. `HELLO`
2. `REGISTER_ACK`
3. `HEARTBEAT`
4. `STATUS_UPDATE`
5. `SYNC_REQUIRED`
6. `SYNC_RESULT`
7. `PLAY`
8. `STOP`
9. `PLAYBACK_STARTED`
10. `PLAYBACK_FINISHED`
11. `PLAYBACK_STOPPED`
12. `PLAYBACK_ERROR`
13. `SET_ENABLED`
14. `ERROR`

This order mirrors the most natural path for building the MVP.
