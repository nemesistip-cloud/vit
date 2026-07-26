from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.modules.platform.integration import platform_integration

router = APIRouter(prefix="/api/platform/events", tags=["Platform Events"])


@router.get("", summary="List recent platform events")
def list_events(event_name: Optional[str] = Query(None)) -> Dict[str, Any]:
    events = platform_integration.events._history if hasattr(platform_integration.events, "_history") else {}
    if event_name:
        items = events.get(event_name, [])
    else:
        items = []
        for bucket in events.values():
            items.extend(bucket)
    return {"events": [
        {
            "event_id": event.event_id,
            "event_type": event.name,
            "sender": event.sender,
            "correlation_id": event.correlation_id,
            "request_id": event.request_id,
            "version": event.version,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata,
            "payload": event.payload,
        }
        for event in items
    ], "total": len(items)}


@router.post("", summary="Publish a platform event")
async def publish_event(
    payload: Dict[str, Any],
    event_name: str = Query(...),
    sender: str = Query("platform_api"),
    correlation_id: Optional[str] = Query(None),
    request_id: Optional[str] = Query(None),
    version: int = Query(1),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    event = await platform_integration.publish_platform_event(
        event_name,
        payload,
        sender=sender,
        correlation_id=correlation_id,
        request_id=request_id,
        metadata={"user_id": str(current_user.id)},
        version=version,
    )
    return {
        "event_id": event.event_id,
        "event_type": event.name,
        "status": "published",
    }
