# app/modules/notifications/routes.py
"""Notification REST + WebSocket API — Module K."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.notifications.service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class PreferencesUpdate(BaseModel):
    prediction_alerts:   Optional[bool] = None
    match_results:       Optional[bool] = None
    wallet_activity:     Optional[bool] = None
    validator_rewards:   Optional[bool] = None
    subscription_expiry: Optional[bool] = None
    email_enabled:       Optional[bool] = None
    telegram_enabled:    Optional[bool] = None
    in_app_enabled:      Optional[bool] = None


# ── REST endpoints ─────────────────────────────────────────────────────────────

@router.get("", summary="List notifications")
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifs = await NotificationService.get_for_user(
        db, current_user.id, limit=limit, unread_only=unread_only
    )
    return [
        {
            "id":         n.id,
            "type":       n.type.value if hasattr(n.type, "value") else n.type,
            "title":      n.title,
            "body":       n.body,
            "is_read":    n.is_read,
            "channel":    n.channel.value if hasattr(n.channel, "value") else n.channel,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.get("/unread-count", summary="Unread notification count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await NotificationService.unread_count(db, current_user.id)
    return {"unread_count": count}


@router.patch("/{notification_id}/read", summary="Mark notification as read")
async def mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = await NotificationService.mark_read(db, current_user.id, notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.post("/read-all", summary="Mark all notifications as read")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await NotificationService.mark_all_read(db, current_user.id)
    return {"marked_read": count}


@router.get("/preferences", summary="Get notification preferences")
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prefs = await NotificationService.get_or_create_prefs(db, current_user.id)
    return {
        "prediction_alerts":   prefs.prediction_alerts,
        "match_results":       prefs.match_results,
        "wallet_activity":     prefs.wallet_activity,
        "validator_rewards":   prefs.validator_rewards,
        "subscription_expiry": prefs.subscription_expiry,
        "email_enabled":       prefs.email_enabled,
        "telegram_enabled":    prefs.telegram_enabled,
        "in_app_enabled":      prefs.in_app_enabled,
    }


@router.patch("/preferences", summary="Update notification preferences")
async def update_preferences(
    updates: PreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = {k: v for k, v in updates.model_dump().items() if v is not None}
    prefs = await NotificationService.update_prefs(db, current_user.id, payload)
    return {
        "prediction_alerts":   prefs.prediction_alerts,
        "match_results":       prefs.match_results,
        "wallet_activity":     prefs.wallet_activity,
        "validator_rewards":   prefs.validator_rewards,
        "subscription_expiry": prefs.subscription_expiry,
        "email_enabled":       prefs.email_enabled,
        "telegram_enabled":    prefs.telegram_enabled,
        "in_app_enabled":      prefs.in_app_enabled,
    }

