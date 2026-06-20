"""Per-user WebSocket connection registry for in-app notification delivery.

Maps a user id to the set of WebSocket connections currently authenticated for
that user (a user may have several tabs/devices open). The dispatcher and the
in-app channel use :data:`user_connection_manager` to push real-time frames.

Mirrors the module-singleton pattern used by
``app.ai.execution.runner_manager``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class UserConnectionManager:
    """Process-level registry of user -> open WebSockets.

    Thread-safety is not required: deployment is single-process with a single
    asyncio event loop. An :class:`asyncio.Lock` still guards mutation so
    interleaved awaits during fan-out cannot corrupt the dict.
    """

    def __init__(self) -> None:
        self._conns: dict[UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        """Register *websocket* as an open connection for *user_id*."""
        async with self._lock:
            self._conns.setdefault(user_id, set()).add(websocket)

    async def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        """Remove *websocket* for *user_id*, pruning empty sets."""
        async with self._lock:
            conns = self._conns.get(user_id)
            if conns is None:
                return
            conns.discard(websocket)
            if not conns:
                self._conns.pop(user_id, None)

    def is_online(self, user_id: UUID) -> bool:
        """Return ``True`` if *user_id* has at least one open connection."""
        return bool(self._conns.get(user_id))

    async def send_to_user(self, user_id: UUID, payload: dict[str, Any]) -> None:
        """JSON-send *payload* to every open socket for *user_id*.

        Sockets that raise on send are pruned (and best-effort closed). Any
        exception is swallowed so a failing client cannot break fan-out.
        """
        async with self._lock:
            sockets = list(self._conns.get(user_id, ()))

        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                logger.debug("Dropping dead notification socket for user %s", user_id)
                dead.append(ws)
                try:
                    await ws.close()
                except Exception:
                    pass

        if dead:
            async with self._lock:
                conns = self._conns.get(user_id)
                if conns is not None:
                    conns.difference_update(dead)
                    if not conns:
                        self._conns.pop(user_id, None)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """JSON-send *payload* to every open socket for every user."""
        async with self._lock:
            user_ids = list(self._conns.keys())
        for user_id in user_ids:
            await self.send_to_user(user_id, payload)


# Module-level singleton.
user_connection_manager = UserConnectionManager()


__all__ = ["UserConnectionManager", "user_connection_manager"]
