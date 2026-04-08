from __future__ import annotations

from enum import Enum


class NodeConnectionState(str, Enum):
    ONLINE = "online"
    STALE = "stale"
    OFFLINE = "offline"


class NodeOperationalState(str, Enum):
    IDLE = "idle"
    SYNCING = "syncing"
    READY = "ready"
    PLAYING = "playing"
    STOPPED = "stopped"
    ERROR = "error"


class SchedulerRuntimeState(str, Enum):
    DISABLED = "disabled"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
