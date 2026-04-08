1) Spec gaps that will block implementation decisions

1. Auth model for dashboard
JWT bearer vs cookie session?
(CSRF implications, refresh flow, logout behavior differ a lot.)
2. Node download auth
How does /api/spots/{id}/download authenticate node requests?

• node token in header?
• short-lived signed URL?
• reuse WS auth token?

3. Node provisioning flow missing
How are node tokens created/rotated/revoked in UI/API?
(Only mentioned in scripts, but not as product flow.)
4. Assignment model unclear
Docs say “define which spots each node should have”, but no concrete model:

• global all-spots?
• per-node assignment table?
• per-group assignment?

5. Scheduler overlap policy not defined
If next interval fires while a node is still playing:

• skip?
• stop-and-replace?
• queue next?
This materially changes behavior.

6. Manual play vs scheduler arbitration undefined
If autoplay running and admin triggers manual play, who wins and for how long?
7. SET_ENABLED=false during playback
Should server also send STOP immediately, or only block future plays?
8. Protocol compatibility/versioning behavior
protocolVersion exists, but no compatibility policy:

• reject unknown versions?
• support range?
• migration strategy?

───

2) Inconsistencies between docs

1. Node states mix connection and operational semantics
online/offline appear both as connection-ish and status values; can cause confusion in DB/UI.
2. PLAYBACK_STOPPED.requestId ambiguity
Example uses stop-200, while description says could be tied to interrupted play request.
Need one rule.
3. SYNC_REQUIRED payload may become huge
No pagination/chunking/compression guidance if spot list grows.
4. REGISTER_ACK.syncRequired vs immediate SYNC_REQUIRED
Both patterns appear; decide canonical flow (flag only vs direct command).

───

3) API design issues to settle now

1. Idempotency on write endpoints (/play, /stop, /scheduler/start)
Need idempotency keys or explicit duplicate semantics.
2. Error schema not standardized
REST and WS both need machine-readable, consistent error model/codes.
3. Bulk command partial success response
/play and /stop target many nodes; response should include per-node dispatch result.
4. No optimistic concurrency for scheduler config
Two admins could race on sequence/interval updates. Add version/ETag.
5. Upload validation policy missing
Max size, MIME allowlist, duration extraction failure behavior, filename sanitation.

───

4) Reliability/operational issues (important since it’ll run on host)

1. Single scheduler instance guarantee
If app runs with >1 worker/replica, APScheduler may double-fire.
Need DB/Redis lock or dedicated scheduler process.
2. WS connection manager durability
In-memory connection registry is fine for one process, fragile if scaled later.
3. Heartbeat timeout strategy
Needs explicit constants and jitter tolerance to avoid false offline on weak Wi‑Fi.
4. Crash recovery semantics
On restart:

• should current_spot_id be reset?
• how to mark stale “playing” states?
• when to trust node re-report vs DB state?

5. Command delivery guarantees
At-most-once vs at-least-once not formally chosen.
Current docs imply retries but not exact guarantees.
6. Storage growth controls missing
Event logs and spot binaries need retention
leanup policy.

───

5) Security issues to treat as must-have even for LAN-first

1. Plain token in HELLO
Acceptable v1 on LAN maybe, but ensure TLS-ready path and rotation support.
2. No rate-limits / lockout policy on admin login
3. No audit trail for admin actions
You log operational events, but not “who changed what” in config/control.
4. File download authorization leakage risk


Must avoid endpoint that allows anyone with spot ID to pull files.

───

6) “Run here and keep running” host concerns (secondary but real)

1. Need service supervision (systemd) and restart policy.
2. Need health/readiness endpoints beyond simple status: ok (DB, storage writable, scheduler alive).
3. Need log rotation + structured logs + basic alerting on repeated disconnect/error bursts.
4. Need backup plan for PostgreSQL + storage/spots.

───

7) Highest-priority clarification list (what I’d ask you first)

1. Exact auth model (JWT vs cookie)
2. Exact node file-download auth mechanism
3. Spot assignment strategy (global/per-node/per-group)
4. Scheduler overlap/manual arbitration rules
5. Single-instance deployment constraint vs future multi-process
6. Command delivery semantics (duplicate handling contract)

───