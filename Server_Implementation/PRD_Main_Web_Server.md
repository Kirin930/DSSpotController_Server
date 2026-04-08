# PRD — Main Web Server for Distributed Spot Controller

## 1. Product Overview

The Main Web Server is the central orchestration system of the Distributed Spot Controller. It manages playback nodes, stores and distributes audio spots, provides the operator dashboard, and controls both manual and automatic spot playback.

This product is the **source of truth** for the whole platform.

---

## 2. Problem Statement

The user needs a centralized system able to control multiple independent speaker nodes remotely. Each node should only play audio when explicitly commanded. The system must support both manual playback and an automated timed sequence of commercial spots.

Without a central controller, node coordination, file consistency, timing control, and real-time operational visibility become difficult and unreliable.

---

## 3. Product Goals

The Main Web Server must allow an operator to:

- manage all nodes from one dashboard
- know which nodes are online and what each one is doing
- upload and manage commercial audio spots
- select which nodes are enabled
- select which nodes participate in autoplay
- manually trigger playback or stop playback on selected nodes
- configure and run automatic sequential playback every X minutes
- receive live status updates from all nodes
- keep a persistent record of system state and playback events

---

## 4. Non-Goals for v1

The first version will not include:
- video playback
- non-Android nodes
- precise sample-level synchronized playback
- public internet deployment by default
- multi-tenant support
- advanced role-based permission models
- campaign calendar logic or complex business rules
- per-node independent playlist engines

---

## 5. Users

## 5.1 Primary User
- system administrator / operator

## 5.2 User Characteristics
The operator needs:
- fast visibility into system status
- a simple way to control nodes
- confidence that playback is happening correctly
- minimal operational complexity

---

## 6. Product Scope

## 6.1 Included in v1
- authenticated admin dashboard
- node registry and live status visualization
- spot upload and management
- node-to-spot synchronization management
- manual playback control
- manual stop control
- autoplay scheduler
- configurable autoplay interval in minutes
- ordered global spot sequence
- event logging
- real-time dashboard updates

---

## 7. Functional Requirements

## 7.1 Authentication and Access

### Requirements
- the dashboard must be protected by admin authentication
- only authenticated admins can upload spots, control playback, or change scheduler settings

### Acceptance Criteria
- unauthenticated users cannot access protected pages
- admin can log in and access the dashboard successfully

---

## 7.2 Node Management

### Description
The system must maintain a registry of all known nodes and show their real-time operational status.

### Functional Requirements
- register and persist nodes
- show node name, ID, version, and last seen time
- show current connection state
- show current operational state
- allow enabling/disabling a node
- allow marking node as included/excluded from autoplay

### Acceptance Criteria
- dashboard displays all nodes
- online/offline state updates in near real time
- enabled state can be changed from dashboard
- autoplay selection can be changed from dashboard

---

## 7.3 Spot Management

### Description
The server must manage a library of audio spots.

### Functional Requirements
- upload audio files
- store file metadata
- view spot list
- activate/deactivate spots
- preserve spot versions/checksums
- expose download endpoint for nodes

### Metadata
Each spot should include at minimum:
- spot ID
- title
- filename
- duration if available
- checksum
- version
- active/inactive state

### Acceptance Criteria
- admin can upload a new spot
- uploaded spot appears in dashboard
- node can download spot through authenticated mechanism
- spot metadata persists in DB

---

## 7.4 Sync Orchestration

### Description
The server must tell nodes what spots they need locally.

### Functional Requirements
- define which spots each node should have
- send sync instructions to nodes
- track sync status/results
- store latest node sync state

### Acceptance Criteria
- node receives sync instructions after changes
- server records success/failure of sync
- dashboard can show whether node is ready or has sync problems

---

## 7.5 Manual Playback Control

### Description
The operator must be able to select one or more nodes and trigger playback of a chosen spot.

### Functional Requirements
- select target nodes
- select one spot
- send play command to selected nodes
- receive started/finished/error events
- display live playback state

### Acceptance Criteria
- admin can manually trigger playback on selected nodes
- nodes report playback start and finish
- dashboard reflects playback state

---

## 7.6 Stop Playback

### Description
The operator must be able to stop playback on one or more nodes.

### Functional Requirements
- send stop command to selected nodes
- update dashboard immediately when node stops or acknowledges stop

### Acceptance Criteria
- stop command reaches selected nodes
- node state moves from playing to stopped or ready
- stop action is logged

---

## 7.7 Autoplay Scheduler

### Description
The server must automatically trigger spot playback on selected nodes every X minutes.

### v1 Model
- one global ordered sequence
- fixed interval in minutes
- target = nodes marked for autoplay and enabled
- all target nodes receive the same current spot

### Functional Requirements
- start autoplay
- stop autoplay
- set interval in minutes
- choose sequence order
- persist scheduler state
- resume consistent scheduler state after restart if desired by implementation

### Acceptance Criteria
- operator can enable autoplay
- operator can set interval
- operator can stop autoplay
- next spot in sequence is triggered every X minutes
- sequence advances correctly

---

## 7.8 Real-Time Status Dashboard

### Description
The operator must see live operational feedback without manual refresh.

### Functional Requirements
- live node status updates
- live playback state updates
- live online/offline state
- live sync state or error visibility

### Acceptance Criteria
- dashboard updates when node state changes
- playback started/finished is visible in near real time
- operator can tell which nodes are ready

---

## 7.9 Event Logging

### Description
The server should keep a historical log of relevant operational events.

### Events to capture
- node connected
- node disconnected
- sync started/completed/failed
- playback command sent
- playback started
- playback finished
- playback stopped
- playback error
- scheduler started/stopped

### Acceptance Criteria
- important events are persisted
- operator can inspect recent history in dashboard or admin log view

---

## 8. Data Model

## 8.1 Node
Fields:
- id
- display_name
- auth_token
- platform
- app_version
- device_model
- enabled
- autoplay_selected
- last_seen_at
- connection_state
- operational_state
- current_spot_id

## 8.2 Spot
Fields:
- id
- title
- filename
- storage_path
- checksum
- version
- duration_ms
- active
- created_at

## 8.3 Playlist / Sequence
Fields:
- id
- name
- ordered spot references

## 8.4 SchedulerConfig
Fields:
- enabled
- interval_minutes
- sequence_id
- current_index
- next_run_at

## 8.5 EventLog
Fields:
- id
- node_id nullable
- spot_id nullable
- event_type
- details
- created_at

---

## 9. User Experience Requirements

## 9.1 Dashboard Main View
Should show:
- all nodes
- online/offline badge
- current state
- current spot if playing
- enabled toggle
- autoplay selection toggle

## 9.2 Spot Management View
Should show:
- uploaded spots
- active/inactive state
- metadata
- upload action

## 9.3 Playback Control View
Should allow:
- selecting nodes
- selecting a spot
- play command
- stop command

## 9.4 Scheduler View
Should allow:
- turning autoplay on/off
- setting interval minutes
- ordering spots in sequence
- seeing current sequence pointer

---

## 10. API and Integration Requirements

The server must provide:
- REST APIs for dashboard actions
- WebSocket endpoint for node communication
- secure download endpoint for spot files

---

## 11. Non-Functional Requirements

## 11.1 Reliability
- server must handle node disconnects gracefully
- state persistence must survive restarts
- scheduler state must not become inconsistent easily

## 11.2 Performance
- dashboard interactions should feel immediate
- node status changes should propagate quickly
- spot downloads should be efficient for LAN usage

## 11.3 Maintainability
- clean separation between API, websocket, scheduler, and persistence
- protocol versioning support
- structured logs

## 11.4 Security
- authenticated admin access
- node token validation
- no unauthenticated playback control
- authenticated file download

---

## 12. Technical Direction

Recommended stack:
- **Backend**: FastAPI
- **Frontend**: React or Next.js
- **Database**: PostgreSQL
- **Scheduler**: APScheduler
- **Realtime**: WebSocket
- **Storage**: local disk for v1

---

## 13. Risks

- node state drift after reconnects
- scheduler duplication after restart if not carefully designed
- file version mismatch between server and nodes
- dashboard confusion if state model is unclear

### Mitigation
- strong state model
- explicit sync flow
- checksum/version validation
- clear event logging
- one authoritative scheduler instance

---

## 14. Success Criteria

The Main Web Server is successful for v1 if:
- admin can see all nodes live
- admin can upload spots
- nodes can sync required files
- admin can manually play and stop spots
- autoplay can play the ordered sequence every X minutes
- node state and playback events are visible live
- system remains stable across normal reconnects and restarts

---

## 15. Future Enhancements

- group-based node control
- richer analytics
- node diagnostics panel
- precise synchronized playback
- volume control
- scheduling by day/time windows
- audit trail and multi-user roles
