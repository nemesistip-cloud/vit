"""app/api/routes/notifications.py — Notification API endpoints (Compatibility layer)

Routes: /api/notifications/* or /notifications/*
Auth: Depends(get_current_user)
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.modules.notifications.models import Notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    read: bool = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List notifications for the current user.
    
    Args:
        limit: Number of notifications to return (1-100)
        offset: Number of notifications to skip
        read: Filter by read status (True/False), or None for all
        
    Returns:
        List of notification objects
    """
    try:
        query = select(Notification).where(Notification.user_id == current_user.id)
        
        if read is not None:
            query = query.where(Notification.is_read == read)
        
        query = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        return [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "read": n.is_read,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "url": getattr(n, 'url', None),
            }
            for n in notifications
        ]
    except Exception as e:
        logger.error(f"Failed to fetch notifications: {e}")
        return []


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    try:
        notification = await db.execute(
            select(Notification).where(
                (Notification.id == notification_id) & (Notification.user_id == current_user.id)
            )
        )
        notif = notification.scalar_one_or_none()
        
        if not notif:
            return {"status": "not_found"}
        
        notif.is_read = True
        await db.commit()
        return {"status": "ok", "id": notification_id}
    except Exception as e:
        logger.error(f"Failed to mark notification read: {e}")
        await db.rollback()
        return {"status": "error", "message": str(e)}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read."""
    try:
        result = await db.execute(
            select(Notification).where(
                (Notification.user_id == current_user.id) & (Notification.is_read == False)
            )
        )
        notifications = result.scalars().all()
        
        for notif in notifications:
            notif.is_read = True
        
        await db.commit()
        return {"status": "ok", "count": len(notifications)}
    except Exception as e:
        logger.error(f"Failed to mark all notifications read: {e}")
        await db.rollback()
        return {"status": "error", "message": str(e)}
