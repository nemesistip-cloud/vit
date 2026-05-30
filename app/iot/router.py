"""app/iot/router.py — REST + WebSocket endpoints for the IoT data layer."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import verify_api_key
from app.db.database import get_db
from app.db.models import IoTEvent
from app.iot.processor import iot_stream, store_and_broadcast
from app.iot.schemas import IngestRequest, IngestResponse, IoTStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/iot", tags=["iot"])


# ── REST: ingest an event ─────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest_event(
    body: IngestRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
) -> IngestResponse:
    """Accept an IoT event, persist it, and broadcast it to stream subscribers."""
    event_id = await store_and_broadcast(
        source=body.source,
        event_type=body.event_type,
        payload=body.payload,
        match_id=body.match_id,
    )
    return IngestResponse(
        event_id=event_id,
        source=body.source,
        event_type=body.event_type,
        match_id=body.match_id,
        received_at=datetime.now(timezone.utc),
    )


# ── REST: recent events ───────────────────────────────────────────────────────

@router.get("/events")
async def list_events(
    limit: int = 50,
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    match_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
) -> Dict[str, Any]:
    """List recent IoT events with optional filters."""
    q = select(IoTEvent).order_by(IoTEvent.created_at.desc()).limit(min(limit, 200))
    if event_type:
        q = q.where(IoTEvent.event_type == event_type)
    if source:
        q = q.where(IoTEvent.source == source)
    if match_id:
        q = q.where(IoTEvent.match_id == match_id)

    rows = await db.execute(q)
    events = rows.scalars().all()

    return {
        "count": len(events),
        "events": [
            {
                "id":           e.id,
                "source":       e.source,
                "event_type":   e.event_type,
                "match_id":     e.match_id,
                "payload":      e.payload,
                "processed":    e.processed,
                "agent_response": e.agent_response,
                "created_at":   e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


# ── REST: status ──────────────────────────────────────────────────────────────

@router.get("/status", response_model=IoTStatusResponse)
async def iot_status(
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
) -> IoTStatusResponse:
    """Return IoT layer health metrics."""
    total_result = await db.execute(select(func.count()).select_from(IoTEvent))
    total = total_result.scalar_one() or 0

    unprocessed_result = await db.execute(
        select(func.count()).select_from(IoTEvent).where(IoTEvent.processed == False)
    )
    unprocessed = unprocessed_result.scalar_one() or 0

    type_result = await db.execute(
        select(IoTEvent.event_type, func.count().label("cnt"))
        .group_by(IoTEvent.event_type)
    )
    type_counts = {row.event_type: row.cnt for row in type_result}

    source_result = await db.execute(
        select(IoTEvent.source, func.count().label("cnt"))
        .group_by(IoTEvent.source)
    )
    source_counts = {row.source: row.cnt for row in source_result}

    return IoTStatusResponse(
        total_events=total,
        unprocessed=unprocessed,
        connected_clients=iot_stream.client_count,
        event_type_counts=type_counts,
        source_counts=source_counts,
    )


# ── WebSocket: live event stream ──────────────────────────────────────────────

@router.websocket("/stream")
async def iot_ws_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint — broadcasts every new IoT event to all connected clients.

    Optional JWT auth: pass ?token=<jwt> to authenticate. Anonymous connections
    are accepted but receive the same public event stream.
    """
    await iot_stream.connect(websocket)
    try:
        await websocket.send_json({
            "type": "connected",
            "ts": datetime.now(timezone.utc).isoformat(),
            "message": "VIT IoT stream connected. Waiting for events...",
        })
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        iot_stream.disconnect(websocket)
