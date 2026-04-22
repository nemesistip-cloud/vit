# app/modules/notifications/websocket.py
"""WebSocket connection manager for real-time notification push."""

import asyncio
import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationConnectionManager:
    """Manages per-user WebSocket connections for live notification delivery."""

    def __init__(self):
        self._connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)
        logger.info(f"WS notification connected: user_id={user_id}")

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)
        logger.info(f"WS notification disconnected: user_id={user_id}")

    async def push(self, user_id: int, payload: dict) -> None:
        conns = self._connections.get(user_id, [])
        dead: List[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast(self, payload: dict) -> None:
        for user_id in list(self._connections.keys()):
            await self.push(user_id, payload)


notification_ws_manager = NotificationConnectionManager()


@router.websocket("/ws/{user_id}")
async def notifications_ws(
    websocket: WebSocket,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    from app.modules.notifications.service import NotificationService

    await notification_ws_manager.connect(user_id, websocket)
    try:
        count = await NotificationService.unread_count(db, user_id)
        await websocket.send_json({"action": "connected", "unread_count": count})

        while True:
            data = await websocket.receive_json()
            if data.get("action") == "ping":
                await websocket.send_json({"action": "pong"})
            elif data.get("action") == "mark_read":
                nid = data.get("notification_id")
                if nid:
                    await NotificationService.mark_read(db, user_id, nid)
                    await websocket.send_json({"action": "marked_read", "notification_id": nid})
    except WebSocketDisconnect:
        notification_ws_manager.disconnect(user_id, websocket)
    except Exception as exc:
        logger.error("Notification WS error user_id=%s error=%s", user_id, exc)
        notification_ws_manager.disconnect(user_id, websocket)
