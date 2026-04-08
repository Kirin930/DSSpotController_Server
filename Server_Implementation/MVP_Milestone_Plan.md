# Distributed Spot Controller — MVP Milestone Plan

## 1. Goal

This plan defines the recommended MVP implementation path for the Distributed Spot Controller.

The goal of the MVP is to prove the full end-to-end workflow:

- server sees nodes live
- server stores spots
- node syncs files locally
- server manually controls playback
- server can autoplay a sequence every X minutes

The milestones are intentionally ordered to reduce technical risk and expose problems early.

---

## 2. MVP Definition

The MVP is complete when all of the following are true:

- one main web server runs successfully
- at least one Android node connects via WebSocket
- the server dashboard shows node online/offline and playback status
- audio spots can be uploaded on the server
- the Android node downloads required spots locally
- the server can trigger play and stop commands
- the server can run automatic sequential playback every X minutes
- playback lifecycle events are visible from the dashboard

---

## 3. Milestone Overview

1. Architecture and protocol lock
2. Backend skeleton
3. Android connection prototype
4. File sync flow
5. Playback flow
6. Dashboard and manual control
7. Scheduler / autoplay
8. Multi-node hardening
9. MVP stabilization and packaging

---

## 4. Milestone 1 — Architecture and Protocol Lock

### Objective
Freeze the first version of the architecture and protocol before implementation.

### Deliverables
- System Architecture Document
- WebSocket Protocol Spec
- PRD for Main Web Server
- PRD for Android Node App
- MVP Milestone Plan

### Acceptance Criteria
- message types are defined
- states are defined
- v1 scope is clear
- development can start without major architecture ambiguity

---

## 5. Milestone 2 — Backend Skeleton

### Objective
Create the first working server foundation.

### Scope
- backend project scaffold
- database setup
- basic authentication for admin
- node registry model
- WebSocket endpoint
- simple node connection tracking
- basic REST endpoints for health and admin

### Suggested Outputs
- FastAPI project initialized
- PostgreSQL connected
- node table created
- WebSocket server accepts and logs connections

### Acceptance Criteria
- backend runs locally
- database migrations work
- a test client can connect through WebSocket
- node online state can be stored/displayed in raw form

---

## 6. Milestone 3 — Android Connection Prototype

### Objective
Create the first Android app able to connect and register.

### Scope
- node ID generation/persistence
- server URL configuration
- token configuration
- WebSocket client
- `HELLO`
- `HEARTBEAT`
- simple status reporting

### Acceptance Criteria
- Android app connects to backend
- server validates node
- dashboard or logs show live node presence
- node reconnects after temporary disconnect

---

## 7. Milestone 4 — File Sync Flow

### Objective
Implement local audio file synchronization.

### Scope
- spot upload endpoint
- spot metadata persistence
- download endpoint
- `SYNC_REQUIRED`
- Android local file store
- checksum/version comparison
- `SYNC_RESULT`

### Acceptance Criteria
- upload a spot on server
- node receives sync request
- node downloads file
- node stores metadata locally
- server records sync result

---

## 8. Milestone 5 — Playback Flow

### Objective
Prove command-based local playback.

### Scope
- `PLAY` command
- `STOP` command
- Android playback engine integration
- `PLAYBACK_STARTED`
- `PLAYBACK_FINISHED`
- `PLAYBACK_STOPPED`
- `PLAYBACK_ERROR`

### Acceptance Criteria
- admin or test endpoint can trigger playback
- Android app plays local file
- stop command works
- playback lifecycle is reported back to server

---

## 9. Milestone 6 — Dashboard and Manual Control

### Objective
Add the operator-facing web UI for core manual operations.

### Scope
- node list page
- live node state updates
- spot library page
- play/stop control UI
- node enable/disable toggle
- autoplay selection toggle

### Acceptance Criteria
- operator can view nodes live
- operator can upload/view spots
- operator can select nodes and trigger playback
- operator can stop selected nodes

---

## 10. Milestone 7 — Scheduler / Autoplay

### Objective
Implement the main automation requirement.

### Scope
- autoplay config model
- interval setting
- ordered global sequence
- scheduler service
- start/stop autoplay controls
- event logging for each scheduled trigger

### Acceptance Criteria
- operator sets interval X minutes
- operator starts autoplay
- next spot in ordered sequence plays on selected nodes
- sequence advances correctly
- operator can stop autoplay

---

## 11. Milestone 8 — Multi-Node Hardening

### Objective
Move from single-node proof to stable multi-node behavior.

### Scope
- multiple Android nodes connected simultaneously
- better disconnect/reconnect handling
- stronger node state reconciliation
- duplicate command handling
- event log view
- clearer error states

### Acceptance Criteria
- multiple nodes can connect at once
- dashboard reflects each node independently
- commands can target subsets of nodes
- reconnects do not break system consistency easily

---

## 12. Milestone 9 — MVP Stabilization and Packaging

### Objective
Prepare the system for practical use.

### Scope
- bug fixing
- operational logging improvements
- configuration cleanup
- deployment scripts
- Android build packaging
- server deployment documentation
- LAN setup instructions

### Acceptance Criteria
- fresh setup can be reproduced
- Android app can be installed and configured cleanly
- common failures are understandable from logs
- system is usable without development-only tooling

---

## 13. Suggested Build Order by Repository

## 13.1 Server Repo First
Recommended sequence:
1. backend skeleton
2. database models
3. websocket gateway
4. file storage
5. playback command endpoints
6. scheduler
7. dashboard frontend

## 13.2 Android Repo
Recommended sequence:
1. settings screen
2. persistent node identity
3. websocket layer
4. local DB
5. sync manager
6. playback engine
7. diagnostics/status UI

---

## 14. Testing Strategy by Milestone

## Milestones 2–3
- local loopback tests
- one Android device
- log-based validation

## Milestones 4–5
- checksum tests
- corrupted file simulation
- repeated play/stop tests

## Milestones 6–7
- dashboard interaction tests
- scheduler interval tests
- sequence rotation validation

## Milestones 8–9
- multi-node tests
- Wi-Fi interruption tests
- app restart tests
- server restart tests

---

## 15. Suggested MVP Backlog Priorities

## P0 — Must Have
- node connection/auth
- node live status
- audio upload
- node sync
- manual play/stop
- autoplay every X minutes
- live playback state

## P1 — Strongly Recommended
- event logging
- reconnect robustness
- enable/disable node
- autoplay target selection

## P2 — Later
- richer UI polish
- diagnostics panel
- advanced analytics
- grouped nodes

---

## 16. Main Risks During MVP

### Risk 1
Android background restrictions interfere with persistent socket behavior.

**Mitigation:** start with controlled device assumptions and use a service strategy suitable for kiosk-like deployment.

### Risk 2
Node state becomes inconsistent after reconnects.

**Mitigation:** define clear reconnect flow and resend sync/status bootstrap.

### Risk 3
Autoplay becomes duplicated or inconsistent after server restart.

**Mitigation:** keep one authoritative scheduler instance and persist scheduler config/state.

### Risk 4
Playback fails due to bad local file state.

**Mitigation:** checksum validation and strong sync reporting.

---

## 17. Recommended Immediate Next Step

After these documents, the best next implementation step is:

1. create the backend repo structure  
2. implement the WebSocket node registration flow  
3. create the Android app skeleton with connection + heartbeat only

That gives the fastest first end-to-end proof and creates the base for everything else.
