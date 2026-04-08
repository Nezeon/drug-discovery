"""
ws/manager.py — MolForge AI WebSocket connection manager.

Maintains a registry of active WebSocket connections keyed by job_id.
All agent status_updates are pushed through this manager to the frontend.

Usage:
    from ws.manager import manager

    # In WebSocket endpoint:
    await manager.connect(job_id, websocket)

    # In pipeline runner (background task):
    await manager.send(job_id, {"type": "agent_start", "agent": "disease_analyst", "message": "..."})

    # On disconnect:
    manager.disconnect(job_id)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages active WebSocket connections indexed by job_id."""

    def __init__(self) -> None:
        # job_id → WebSocket
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection for the given job."""
        await websocket.accept()
        self._connections[job_id] = websocket
        logger.info("WebSocket connected: job_id=%s (total active: %d)", job_id, len(self._connections))

    def disconnect(self, job_id: str) -> None:
        """Remove a connection from the registry (does NOT close the socket)."""
        if job_id in self._connections:
            del self._connections[job_id]
            logger.info("WebSocket disconnected: job_id=%s (total active: %d)", job_id, len(self._connections))

    async def send(self, job_id: str, message: dict[str, Any]) -> None:
        """
        Send a JSON message to the WebSocket for the given job.
        Silently no-ops if no connection exists (job may have finished).
        """
        websocket = self._connections.get(job_id)
        if websocket is None:
            logger.debug("send() called for job_id=%s but no active connection — skipping", job_id)
            return
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as exc:
            logger.warning("WebSocket send failed for job_id=%s: %s", job_id, exc)
            self.disconnect(job_id)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a message to all active connections (used for system announcements)."""
        for job_id in list(self._connections.keys()):
            await self.send(job_id, message)

    @property
    def active_count(self) -> int:
        return len(self._connections)


# Singleton — import this everywhere
manager = WebSocketManager()
