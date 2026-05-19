"""
Module F — Real-time WebSocket Manager
Broadcasts live odds updates and pipeline events to connected clients.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class OddsConnectionManager:
    """
    Manages WebSocket connections for real-time odds broadcasting.

    Clients can subscribe to specific leagues or receive all updates
    by connecting without a league filter.

    Protocol (client → server):
        {"action": "subscribe", "league": "premier_league"}
        {"action": "subscribe", "league": "*"}   # all leagues
        {"action": "ping"}

    Protocol (server → client):
        {"type": "odds_update", "match_id": "...", "league": "...", "odds": {...}, "ts": "..."}
        {"type": "pipeline_event", "event": "run_complete", "matches": 42, "ts": "..."}
        {"type": "pong", "ts": "..."}
        {"type": "error", "message": "..."}
    """

    def __init__(self):
        # ws → set of subscribed leagues ("*" means all)
        self._connections: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = {"*"}   # default: all leagues
        logger.info(f"WS client connected. Total: {len(self._connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._connections.pop(websocket, None)
        logger.info(f"WS client disconnected. Total: {len(self._connections)}")

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def handle_message(self, websocket: WebSocket, data: str):
        try:
            msg = json.loads(data)
        except json.JSONDecodeError:
            await self._send(websocket, {"type": "error", "message": "Invalid JSON"})
            return

        action = msg.get("action")

        if action == "subscribe":
            league = msg.get("league", "*")
            async with self._lock:
                self._connections[websocket] = {league}
            await self._send(websocket, {"type": "subscribed", "league": league, "ts": _now()})

        elif action == "ping":
            await self._send(websocket, {"type": "pong", "ts": _now()})

        else:
            await self._send(websocket, {"type": "error", "message": f"Unknown action: {action}"})

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def broadcast_odds_update(self, match_id: str, league: str, odds: dict):
        """Push a live odds update to all clients subscribed to this league."""
        payload = {
            "type": "odds_update",
            "match_id": match_id,
            "league": league,
            "odds": odds,
            "ts": _now(),
        }
        await self._broadcast(payload, league_filter=league)

    async def broadcast_pipeline_event(self, event: str, **kwargs):
        """Push a pipeline lifecycle event (run started, completed, failed)."""
        payload = {"type": "pipeline_event", "event": event, "ts": _now(), **kwargs}
        await self._broadcast(payload, league_filter=None)

    async def broadcast_feature_ready(self, match_id: str, league: str):
        """Notify clients that fresh features are available for a match."""
        payload = {
            "type": "features_ready",
            "match_id": match_id,
            "league": league,
            "ts": _now(),
        }
        await self._broadcast(payload, league_filter=league)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _broadcast(self, payload: dict, league_filter: Optional[str]):
        """Send payload to all relevant connected clients."""
        dead: list = []
        async with self._lock:
            connections = dict(self._connections)

        for ws, subscriptions in connections.items():
            if league_filter is None or "*" in subscriptions or league_filter in subscriptions:
                try:
                    await ws.send_text(json.dumps(payload))
                except Exception:
                    dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)

    async def _send(self, websocket: WebSocket, payload: dict):
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.warning(f"Failed to send to WS client: {e}")

    @property
    def connection_count(self) -> int:
        return len(self._connections)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Module-level singleton shared across the app
odds_manager = OddsConnectionManager()
