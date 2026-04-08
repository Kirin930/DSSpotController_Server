from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket


@dataclass(slots=True)
class CommandAcknowledgement:
    message_type: str
    payload: dict[str, Any]


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._pending: dict[tuple[str, str], asyncio.Future[CommandAcknowledgement]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, node_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            existing = self._connections.get(node_id)
            self._connections[node_id] = websocket
        if existing is not None and existing is not websocket:
            await existing.close()

    async def disconnect(self, node_id: str) -> None:
        async with self._lock:
            self._connections.pop(node_id, None)
            pending_keys = [
                key for key in self._pending.keys() if key[0] == node_id
            ]
            for key in pending_keys:
                future = self._pending.pop(key)
                if not future.done():
                    future.cancel()

    def is_connected(self, node_id: str) -> bool:
        return node_id in self._connections

    async def send_to_node(self, node_id: str, message: dict[str, Any]) -> bool:
        websocket = self._connections.get(node_id)
        if websocket is None:
            return False
        try:
            await websocket.send_json(message)
        except Exception:
            return False
        return True

    def create_ack_future(
        self, node_id: str, request_id: str
    ) -> asyncio.Future[CommandAcknowledgement]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[CommandAcknowledgement] = loop.create_future()
        self._pending[(node_id, request_id)] = future
        return future

    def resolve_ack(
        self,
        node_id: str,
        request_id: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> None:
        future = self._pending.pop((node_id, request_id), None)
        if future is not None and not future.done():
            future.set_result(
                CommandAcknowledgement(message_type=message_type, payload=payload)
            )

    def cancel_ack(self, node_id: str, request_id: str) -> None:
        future = self._pending.pop((node_id, request_id), None)
        if future is not None and not future.done():
            future.cancel()
