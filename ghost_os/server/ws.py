"""WebSocket connection manager for real-time telemetry streaming."""

from __future__ import annotations
import json
import logging
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger("ghost_os.ws")


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast_json(self, data: dict) -> None:
        """Broadcasts a JSON object to all connected clients."""
        if not self.active_connections:
            return
        message = json.dumps(data)
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.add(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)
