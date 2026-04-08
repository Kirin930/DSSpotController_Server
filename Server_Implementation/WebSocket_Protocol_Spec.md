# Distributed Spot Controller — WebSocket Protocol Specification

## 1. Purpose

This document defines the WebSocket protocol between the **Main Web Server** and the **Android Node Application** for the Distributed Spot Controller.

The protocol is designed to support:
- node registration
- authentication
- presence and heartbeats
- status reporting
- synchronization control
- playback commands
- error handling

This specification focuses on **server ↔ node communication**, not frontend dashboard communication.

---

## 2. Design Principles

- JSON messages only
- one message per frame
- server is authoritative
- nodes are execution agents
- commands are explicit
- every important action is acknowledged through status or event messages
- protocol should be versionable

---

## 3. Connection Lifecycle

## 3.1 Basic Sequence
1. Node opens WebSocket connection to server.
2. Node sends `HELLO`.
3. Server validates identity/token.
4. Server replies `REGISTER_ACK` or `ERROR`.
5. Connection becomes active.
6. Periodic heartbeat keeps connection healthy.
7. Server may send commands at any time while connected.

---

## 4. Message Envelope

All protocol messages should follow a common envelope structure.

```json
{
  "type": "MESSAGE_TYPE",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:00:00Z",
  "requestId": "optional-correlation-id",
  "payload": {}
}
```

### Field definitions
- `type`: message type identifier
- `protocolVersion`: protocol version integer
- `timestamp`: ISO 8601 UTC timestamp
- `requestId`: optional correlation ID for tracing commands/events
- `payload`: type-specific object

---

## 5. Authentication Model

Each node must have:
- a persistent `nodeId`
- a node authentication token provisioned by the server or admin

Authentication happens inside the `HELLO` message.

Example:
```json
{
  "type": "HELLO",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:00:00Z",
  "payload": {
    "nodeId": "android-node-001",
    "authToken": "node-secret-token",
    "displayName": "Entrance Speaker",
    "platform": "android",
    "appVersion": "1.0.0"
  }
}
```

If invalid, server responds with `ERROR` and may close the socket.

---

## 6. Message Types Overview

## 6.1 Node → Server
- `HELLO`
- `HEARTBEAT`
- `STATUS_UPDATE`
- `SYNC_RESULT`
- `PLAYBACK_STARTED`
- `PLAYBACK_FINISHED`
- `PLAYBACK_STOPPED`
- `PLAYBACK_ERROR`
- `ERROR`

## 6.2 Server → Node
- `REGISTER_ACK`
- `PING`
- `SYNC_REQUIRED`
- `PLAY`
- `STOP`
- `SET_ENABLED`
- `CONFIG_UPDATE`
- `ERROR`

---

## 7. Node → Server Messages

## 7.1 HELLO
Sent immediately after connection opens.

### Purpose
- identify the node
- authenticate the node
- provide version/platform metadata

### Example
```json
{
  "type": "HELLO",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:00:00Z",
  "payload": {
    "nodeId": "android-node-001",
    "authToken": "node-secret-token",
    "displayName": "Entrance Speaker",
    "platform": "android",
    "appVersion": "1.0.0",
    "deviceModel": "Samsung Galaxy A14"
  }
}
```

---

## 7.2 HEARTBEAT
Sent periodically while connected.

### Purpose
- maintain liveness
- allow server to track connection health
- optionally include lightweight status snapshot

### Suggested interval
Every 15 to 30 seconds.

### Example
```json
{
  "type": "HEARTBEAT",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:00:30Z",
  "payload": {
    "nodeId": "android-node-001",
    "status": "ready",
    "currentSpotId": null
  }
}
```

---

## 7.3 STATUS_UPDATE
Sent when a node state changes.

### Example state changes
- idle → syncing
- syncing → ready
- ready → error
- playing → idle

### Example
```json
{
  "type": "STATUS_UPDATE",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:01:00Z",
  "payload": {
    "nodeId": "android-node-001",
    "status": "ready",
    "currentSpotId": null,
    "details": "Sync completed successfully"
  }
}
```

---

## 7.4 SYNC_RESULT
Sent after a sync cycle completes.

### Example
```json
{
  "type": "SYNC_RESULT",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:02:00Z",
  "requestId": "sync-req-001",
  "payload": {
    "nodeId": "android-node-001",
    "result": "success",
    "downloadedSpotIds": ["spot-001", "spot-002"],
    "updatedSpotIds": [],
    "failedSpotIds": []
  }
}
```

### Failure example
```json
{
  "type": "SYNC_RESULT",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:02:00Z",
  "requestId": "sync-req-001",
  "payload": {
    "nodeId": "android-node-001",
    "result": "partial_failure",
    "downloadedSpotIds": ["spot-001"],
    "updatedSpotIds": [],
    "failedSpotIds": ["spot-002"],
    "errorMessage": "Checksum mismatch for spot-002"
  }
}
```

---

## 7.5 PLAYBACK_STARTED
Sent when playback actually begins.

```json
{
  "type": "PLAYBACK_STARTED",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:05:00Z",
  "requestId": "play-cmd-145",
  "payload": {
    "nodeId": "android-node-001",
    "spotId": "spot-001"
  }
}
```

---

## 7.6 PLAYBACK_FINISHED
Sent when playback completes naturally.

```json
{
  "type": "PLAYBACK_FINISHED",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:05:23Z",
  "requestId": "play-cmd-145",
  "payload": {
    "nodeId": "android-node-001",
    "spotId": "spot-001",
    "durationMs": 23000
  }
}
```

---

## 7.7 PLAYBACK_STOPPED
Sent when playback is interrupted by a stop request or replacement.

```json
{
  "type": "PLAYBACK_STOPPED",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:05:10Z",
  "requestId": "play-cmd-145",
  "payload": {
    "nodeId": "android-node-001",
    "spotId": "spot-001",
    "reason": "server_stop_command"
  }
}
```

---

## 7.8 PLAYBACK_ERROR
Sent when playback fails.

```json
{
  "type": "PLAYBACK_ERROR",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:05:02Z",
  "requestId": "play-cmd-145",
  "payload": {
    "nodeId": "android-node-001",
    "spotId": "spot-001",
    "errorCode": "FILE_NOT_FOUND",
    "errorMessage": "Local audio file is missing"
  }
}
```

---

## 7.9 ERROR
Generic error from node to server when a request cannot be handled.

```json
{
  "type": "ERROR",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:06:00Z",
  "requestId": "sync-req-002",
  "payload": {
    "nodeId": "android-node-001",
    "errorCode": "INVALID_MESSAGE",
    "errorMessage": "Payload missing required field 'spots'"
  }
}
```

---

## 8. Server → Node Messages

## 8.1 REGISTER_ACK
Sent after successful `HELLO`.

### Purpose
- confirms registration
- communicates initial node config
- optionally indicates whether sync is needed

```json
{
  "type": "REGISTER_ACK",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:00:01Z",
  "payload": {
    "nodeId": "android-node-001",
    "enabled": true,
    "autoplaySelected": true,
    "syncRequired": true
  }
}
```

---

## 8.2 PING
Optional server-side liveness probe.

```json
{
  "type": "PING",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:00:45Z",
  "payload": {}
}
```

The node may respond with `HEARTBEAT`.

---

## 8.3 SYNC_REQUIRED
Instructs the node to reconcile local files with the server assignment.

```json
{
  "type": "SYNC_REQUIRED",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:01:30Z",
  "requestId": "sync-req-001",
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

### Node behavior
- compare by `spotId`, `version`, and `checksum`
- download missing or outdated files
- remove files no longer assigned if desired by policy
- report `SYNC_RESULT`

---

## 8.4 PLAY
Instructs the node to play one local spot immediately.

```json
{
  "type": "PLAY",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:05:00Z",
  "requestId": "play-cmd-145",
  "payload": {
    "spotId": "spot-001",
    "replaceIfPlaying": true
  }
}
```

### Node behavior
- verify local file exists and is valid
- if another spot is playing and `replaceIfPlaying = true`, stop current playback and start the new one
- send `PLAYBACK_STARTED`, then terminal playback event

---

## 8.5 STOP
Instructs the node to stop playback immediately.

```json
{
  "type": "STOP",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:05:10Z",
  "requestId": "stop-cmd-200",
  "payload": {}
}
```

### Node behavior
- stop current playback if any
- send `PLAYBACK_STOPPED` if a spot was active
- otherwise optionally send `STATUS_UPDATE`

---

## 8.6 SET_ENABLED
Communicates whether the node should remain operational.

```json
{
  "type": "SET_ENABLED",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:10:00Z",
  "payload": {
    "enabled": false
  }
}
```

### v1 interpretation
If disabled:
- node stays connected
- node does not execute play commands
- node may still sync and report status

---

## 8.7 CONFIG_UPDATE
Used for future-friendly updates to node runtime configuration.

```json
{
  "type": "CONFIG_UPDATE",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:12:00Z",
  "payload": {
    "autoplaySelected": true
  }
}
```

---

## 8.8 ERROR
Generic server-side error.

```json
{
  "type": "ERROR",
  "protocolVersion": 1,
  "timestamp": "2026-03-17T12:13:00Z",
  "requestId": "play-cmd-145",
  "payload": {
    "errorCode": "UNKNOWN_SPOT",
    "errorMessage": "Requested spot does not exist on server"
  }
}
```

---

## 9. State Semantics

## 9.1 Allowed Node Status Values
Suggested normalized values:
- `offline`
- `online`
- `idle`
- `syncing`
- `ready`
- `playing`
- `stopped`
- `error`

### Notes
- `offline` is mainly server-derived
- `online` means connected but not necessarily ready
- `ready` means connected and able to play
- `playing` means actively reproducing audio

---

## 10. Timeout Rules

## 10.1 Heartbeat Timeout
If the server does not receive a heartbeat for a configured period:
- node is marked offline
- active playback state is considered stale
- dashboard updates immediately

Suggested offline threshold:
- 2 or 3 missed heartbeat windows

Example:
- heartbeat every 20 seconds
- offline after 60 seconds without heartbeat

---

## 11. Idempotency and Retries

### HELLO
Safe to resend after reconnect.

### SYNC_REQUIRED
Can be re-issued by server at any time.

### PLAY
A duplicate `PLAY` with same `requestId` should be handled carefully.
Recommended:
- node tracks most recent command IDs briefly
- repeated identical command IDs are ignored or acknowledged safely

### STOP
Should be safe to apply multiple times.

---

## 12. Error Handling Rules

### Protocol errors
If required fields are missing or malformed:
- receiver sends `ERROR`
- severe violations may cause connection close

### Authentication errors
If token invalid:
- server sends `ERROR`
- server closes connection

### Playback errors
Node must send `PLAYBACK_ERROR` with a machine-readable `errorCode`

Suggested error codes:
- `FILE_NOT_FOUND`
- `FILE_CORRUPTED`
- `PLAYBACK_ENGINE_FAILURE`
- `NODE_DISABLED`
- `INVALID_STATE`
- `UNAUTHORIZED`
- `INVALID_MESSAGE`

---

## 13. Ordering Rules

Because WebSocket preserves message order per connection, messages should arrive in order on a single socket.

However, implementation must still tolerate:
- reconnects
- race conditions between stop/play
- stale commands received just before disconnect

Recommended:
- include `requestId`
- optionally include a server command sequence number later

---

## 14. Future Extensions

Possible future protocol additions:
- `PLAY_AT` with absolute server timestamp for synchronized starts
- `SET_VOLUME`
- `REQUEST_STATUS`
- `DELETE_LOCAL_SPOT`
- `DOWNLOAD_PROGRESS`
- richer diagnostics/telemetry

---

## 15. v1 Operational Rules Summary

- node connects and authenticates using `HELLO`
- server confirms using `REGISTER_ACK`
- node sends periodic `HEARTBEAT`
- node reports state via `STATUS_UPDATE`
- server requests file reconciliation via `SYNC_REQUIRED`
- node reports completion via `SYNC_RESULT`
- server controls playback via `PLAY` and `STOP`
- node reports playback lifecycle events
- server is always authoritative for when playback happens

---

## 16. Recommended v1 Contract

For the MVP, the minimum mandatory message set should be:

### Node → Server
- `HELLO`
- `HEARTBEAT`
- `STATUS_UPDATE`
- `SYNC_RESULT`
- `PLAYBACK_STARTED`
- `PLAYBACK_FINISHED`
- `PLAYBACK_STOPPED`
- `PLAYBACK_ERROR`

### Server → Node
- `REGISTER_ACK`
- `SYNC_REQUIRED`
- `PLAY`
- `STOP`
- `SET_ENABLED`
- `ERROR`

This keeps the protocol lean while covering all required orchestration behavior.
