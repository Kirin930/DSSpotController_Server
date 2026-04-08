# Distributed Spot Controller — System Architecture Document

## 1. Purpose

This document defines the system architecture for the **Distributed Spot Controller**, a platform that allows a central server to orchestrate audio spot playback across multiple independent speaker nodes.

The system is split into two main parts:

1. **Main Web Server**  
   Central orchestration layer, dashboard, scheduling engine, source of truth, and node manager.

2. **Android Node Application**  
   Distributed playback client installed on each Android device connected to a speaker.

The first release focuses on:
- Android-only nodes
- audio-only playback
- LAN-first deployment
- central control through WebSocket
- local audio caching on each node
- manual and automatic playback modes

---

## 2. Product Goals

The system must allow an operator to:

- manage multiple playback nodes from one web dashboard
- know which nodes are online, ready, playing, or in error
- upload and manage commercial audio spots
- decide which nodes are enabled or excluded
- trigger playback manually on one or more nodes
- start and stop automatic sequential playback
- choose the autoplay interval in minutes
- ensure playback happens only when the server commands it

---

## 3. High-Level Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                    Main Web Server                       │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │ Admin UI     │   │ REST API     │   │ WebSocket    │  │
│  │ Dashboard    │   │ + Auth       │   │ Gateway      │  │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘  │
│         │                  │                  │          │
│  ┌──────▼──────────────────▼──────────────────▼───────┐  │
│  │                Orchestration Layer                 │  │
│  │  - Node registry                                   │  │
│  │  - Playback control                                │  │
│  │  - Sync management                                 │  │
│  │  - Scheduler / autoplay                            │  │
│  │  - Event logging                                   │  │
│  └──────┬───────────────────────────────┬─────────────┘  │
│         │                               │                │
│  ┌──────▼───────┐               ┌───────▼────────┐       │
│  │ PostgreSQL   │               │ Spot Storage   │       │
│  │ DB           │               │ Audio Files    │       │
│  └──────────────┘               └────────────────┘       │
└──────────────────────────────────────────────────────────┘
                         │
                         │ WebSocket + HTTP(S)
                         │
     ┌───────────────────┼────────────────────┬───────────────────┐
     │                   │                    │                   │
┌────▼────┐        ┌─────▼────┐         ┌────▼────┐         ┌────▼────┐
│ Node A  │        │ Node B   │         │ Node C  │         │ Node N  │
│ Android │        │ Android  │         │ Android │         │ Android │
│ App     │        │ App      │         │ App     │         │ App     │
└─────────┘        └──────────┘         └─────────┘         └─────────┘
```

---

## 4. Architectural Principles

### 4.1 Server as Source of Truth
The server is authoritative for:
- node enablement
- autoplay participation
- playback commands
- spot library
- playback order
- scheduler timing
- system state displayed in dashboard

Nodes must not autonomously decide when to play in production.

### 4.2 Thin Playback Nodes
Nodes are intentionally simple. Their job is to:
- connect
- sync
- cache files
- play audio
- report status

### 4.3 Local File Availability
Each node downloads its required audio files locally so that playback is fast and does not depend on real-time streaming during execution.

### 4.4 Real-Time Control
Node control and state propagation happen through persistent WebSocket connections.

### 4.5 Operational Simplicity
The first deployment is LAN-first and optimized for ease of implementation, reliability, and maintainability.

---

## 5. Core Components

## 5.1 Main Web Server

### Responsibilities
- authenticate admins
- manage nodes
- manage spot library
- manage playlist/sequence
- coordinate synchronization
- send playback commands
- run autoplay scheduler
- collect node events
- expose dashboard APIs
- persist system state

### Internal Subsystems
- **Admin UI**
- **Backend API**
- **WebSocket Gateway**
- **Scheduler**
- **Node State Manager**
- **Spot Manager**
- **Logging/Event Service**
- **Persistence Layer**

---

## 5.2 Android Node Application

### Responsibilities
- maintain persistent identity
- connect to server via WebSocket
- authenticate to server
- receive commands
- download/update spot files
- store files locally
- play/stop audio
- report playback and health status
- recover from connection or app restarts

### Internal Subsystems
- **Node Identity Manager**
- **WebSocket Client**
- **Sync Manager**
- **Local Storage / Metadata DB**
- **Playback Engine**
- **Status Reporter**
- **Recovery / Background Services**

---

## 6. Main Data Flows

## 6.1 Node Registration and Presence
1. Node starts.
2. Node loads persistent node ID and token.
3. Node connects to server WebSocket.
4. Node sends `HELLO`.
5. Server validates node and marks it online.
6. Server returns node config and sync instructions if needed.

## 6.2 Spot Synchronization
1. Server determines which spots the node must have.
2. Server sends `SYNC_REQUIRED`.
3. Node compares versions/checksums.
4. Node downloads missing or outdated files over HTTP.
5. Node verifies checksum.
6. Node updates local metadata.
7. Node reports `SYNC_RESULT`.

## 6.3 Manual Playback
1. Admin selects nodes in dashboard.
2. Admin triggers play for one specific spot.
3. Server sends `PLAY` to selected nodes.
4. Nodes play local file.
5. Nodes report `PLAYBACK_STARTED`.
6. Nodes report `PLAYBACK_FINISHED` or `PLAYBACK_ERROR`.

## 6.4 Automatic Playback
1. Admin enables autoplay and sets interval.
2. Scheduler runs every X minutes.
3. Server selects next spot from ordered sequence.
4. Server sends `PLAY` to all enabled autoplay nodes.
5. Sequence index advances.
6. Events are logged.

---

## 7. Logical Domains

## 7.1 Node Domain
Represents all connected playback agents.

Key properties:
- identity
- connectivity
- readiness
- enabled/disabled state
- autoplay selection
- current playback state
- installed spot versions

## 7.2 Spot Domain
Represents uploaded audio assets and metadata.

Key properties:
- title
- filename
- duration
- checksum
- version
- active status
- storage location

## 7.3 Playback Domain
Represents manual and automatic playback orchestration.

Key properties:
- current spot
- target nodes
- command status
- playback lifecycle events

## 7.4 Scheduling Domain
Represents the autoplay loop.

Key properties:
- enabled
- interval minutes
- sequence ordering
- target nodes
- next run time
- current index

---

## 8. State Model

## 8.1 Node Connection State
- `offline`
- `connecting`
- `online`

## 8.2 Node Operational State
- `idle`
- `syncing`
- `ready`
- `playing`
- `stopped`
- `error`

## 8.3 Scheduler State
- `disabled`
- `running`
- `paused`
- `error`

---

## 9. Storage Strategy

## 9.1 Server Storage
Use two storage types:

### Database
Stores:
- nodes
- spot metadata
- playlist order
- scheduler config
- event logs
- node states
- file assignments

### File Storage
Stores:
- uploaded audio files
- versioned spot binaries

For v1, local disk storage is acceptable.

## 9.2 Node Storage
Each Android node stores:
- local audio files
- local metadata DB
- node settings
- playback state snapshot if useful

Use app-private storage to avoid accidental modification.

---

## 10. Communication Strategy

## 10.1 Control Channel
A persistent WebSocket connection is used for:
- registration
- heartbeats
- status updates
- play/stop commands
- sync instructions

## 10.2 File Download Channel
Regular HTTP(S) endpoints are used for downloading audio files.

This separation keeps file transfers simpler and avoids large binary transfers over WebSocket.

---

## 11. Scheduling Model

The scheduler is fully server-side.

### v1 behavior
- one global ordered sequence
- one global interval in minutes
- all selected autoplay nodes receive the same current spot
- trigger is based on fixed interval timing
- nodes do not locally schedule playback

### Rationale
This is the simplest architecture and keeps behavior deterministic.

---

## 12. Reliability and Recovery

## 12.1 Node Recovery
The Android node must:
- reconnect automatically after disconnect
- re-announce itself after reconnect
- request or accept sync check after reconnect
- stop considering itself authorized if token invalid
- gracefully handle missing files and playback errors

## 12.2 Server Recovery
The server must:
- reload scheduler state on restart
- restore node registry from DB
- rebuild dashboard state from persisted state + live connections
- mark nodes offline if heartbeats stop

## 12.3 Network Interruption
If network is lost:
- node becomes disconnected
- server marks node offline after timeout
- node must never play automatically while disconnected
- node resumes normal operation only after reconnect and resync validation

---

## 13. Security Model

### v1 minimum security
- authenticated admin dashboard
- token-authenticated nodes
- authenticated file download endpoints
- no anonymous playback or sync operations
- LAN deployment by default

### Later improvements
- TLS termination
- signed download URLs
- device provisioning flow
- audit logs
- role-based access control

---

## 14. Main Technology Direction

## 14.1 Server
Recommended stack:
- **Backend**: FastAPI
- **Frontend**: React or Next.js
- **Database**: PostgreSQL
- **Scheduling**: APScheduler
- **Realtime**: WebSocket
- **Storage**: local disk for v1

## 14.2 Android
Recommended stack:
- **Language**: Kotlin
- **UI**: Jetpack Compose
- **Playback**: Media3 / ExoPlayer
- **Local DB**: Room
- **Realtime**: OkHttp WebSocket
- **Background tasks**: WorkManager

---

## 15. Constraints and Non-Goals for v1

### Included
- Android nodes only
- audio spots only
- manual play/stop
- autoplay every X minutes
- local file sync on nodes
- live dashboard state
- per-node enablement

### Not included in v1
- iOS nodes
- video spots
- sample-perfect synchronized playback
- WAN/public internet deployment by default
- complex campaign rules
- per-node custom playlist logic
- advanced analytics

---

## 16. Future Extensions

- precise synchronized playback using scheduled timestamps
- per-node or per-group playlists
- campaign calendars
- volume control and remote device settings
- richer observability and metrics
- iOS or desktop nodes
- server clustering
- cloud deployment

---

## 17. Summary

The Distributed Spot Controller should be implemented as a central orchestration server plus lightweight Android playback nodes. The server owns the logic and timing; the nodes own reliable local playback and reporting. This architecture is scalable enough for an MVP, simple enough to build cleanly, and structured to evolve later into a more advanced distributed media control platform.
