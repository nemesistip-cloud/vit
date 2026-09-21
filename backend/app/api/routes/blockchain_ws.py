"""
Blockchain WebSocket API — Real-time event streaming for blocks and transactions.
"""
import asyncio
import json
import logging
from typing import List, Dict, Set, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.event_bus import event_bus, Event
from vit_chain.consensus.events import ConsensusEventBus
from app.services.cache import _get_redis

router = APIRouter(prefix="/api/chain/ws", tags=["Blockchain WebSocket"])
logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.redis_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"[ws] New connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"[ws] Disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return

        payload = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def start_redis_listener(self):
        """Listen to Redis consensus events and broadcast them."""
        r = _get_redis()
        if not r:
            logger.warning("[ws] Redis not available, consensus events will not be streamed.")
            return

        pubsub = r.pubsub()
        await pubsub.subscribe(ConsensusEventBus.CHANNEL)
        logger.info(f"[ws] Subscribed to Redis channel: {ConsensusEventBus.CHANNEL}")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self.broadcast({
                        "event": data.get("type"),
                        "data": data.get("data"),
                        "source": "consensus"
                    })
        except Exception as e:
            logger.error(f"[ws] Redis listener error: {e}")
        finally:
            await pubsub.unsubscribe(ConsensusEventBus.CHANNEL)

    async def on_internal_event(self, event: Event):
        """Handle internal events from the Kernel EventBus."""
        # Only stream relevant blockchain events
        if event.name in ["BlockAdded", "TransactionAccepted", "TransactionRejected", "LedgerVerified"]:
            await self.broadcast({
                "event": event.name,
                "data": event.payload,
                "source": "kernel",
                "timestamp": event.timestamp.isoformat()
            })

manager = SubscriptionManager()

# Hook into the internal event bus
@event_bus.subscribe_all
async def internal_event_proxy(event: Event):
    await manager.on_internal_event(event)

@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    # Ensure redis listener is running (lazy start)
    if manager.redis_task is None or manager.redis_task.done():
        manager.redis_task = asyncio.create_task(manager.start_redis_listener())

    try:
        while True:
            # Keep connection open and handle incoming client messages if any
            data = await websocket.receive_text()
            # Handle client-side subscriptions or heartbeats here
            await websocket.send_text(json.dumps({"status": "received", "echo": data}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[ws] WebSocket error: {e}")
        manager.disconnect(websocket)
