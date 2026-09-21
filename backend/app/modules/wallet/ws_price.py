# app/modules/wallet/ws_price.py
"""VITCoin real-time price WebSocket endpoint."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.modules.wallet.pricing import VITCoinPricingEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["wallet-ws"])

_connections: set[WebSocket] = set()


async def _get_price_payload() -> dict:
    try:
        async with AsyncSessionLocal() as db:
            engine = VITCoinPricingEngine(db)
            prices = await engine.get_current_price()
            supply = await engine.get_circulating_supply()
            return {
                "type": "price_update",
                "price_usd": float(prices["usd"]),
                "price_ngn": float(prices["ngn"]),
                "price_usdt": float(prices["usdt"]),
                "price_pi": float(prices["pi"]),
                "circulating_supply": float(supply),
                "market_cap_usd": float(prices["usd"] * supply),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        logger.error(f"ws_price: failed to fetch price: {e}")
        return {
            "type": "price_update",
            "price_usd": 0.10,
            "price_ngn": 158.0,
            "price_usdt": 0.10,
            "price_pi": 0.318,
            "circulating_supply": 10_000_000.0,
            "market_cap_usd": 1_000_000.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def broadcast_price() -> None:
    """Broadcast the current VITCoin price to all connected clients."""
    if not _connections:
        return
    payload = await _get_price_payload()
    message = json.dumps(payload)
    dead: set[WebSocket] = set()
    for ws in list(_connections):
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)


async def price_broadcast_loop(interval_seconds: int = 30) -> None:
    """Background loop that broadcasts price every N seconds."""
    while True:
        await asyncio.sleep(interval_seconds)
        await broadcast_price()


@router.websocket("/ws/wallet/price")
async def vitcoin_price_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.add(websocket)
    logger.info(f"ws_price: client connected ({len(_connections)} total)")

    payload = await _get_price_payload()
    try:
        await websocket.send_text(json.dumps(payload))
    except Exception:
        _connections.discard(websocket)
        return

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(json.dumps({"type": "heartbeat"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"ws_price: connection error: {e}")
    finally:
        _connections.discard(websocket)
        logger.info(f"ws_price: client disconnected ({len(_connections)} remaining)")
