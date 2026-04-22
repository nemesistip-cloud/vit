# app/modules/notifications/service.py
"""Notification service — queue, templates, multi-channel delivery."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import (
    Notification, NotificationChannel, NotificationPreference, NotificationType
)
from app.modules.notifications.websocket import notification_ws_manager

logger = logging.getLogger(__name__)


# ── Templates ─────────────────────────────────────────────────────────────────

TEMPLATES: dict[str, tuple[str, str]] = {
    NotificationType.PREDICTION_ALERT.value: (
        "🎯 New Prediction Alert",
        "A new prediction is available for {match}. Confidence: {confidence}%.",
    ),
    NotificationType.MATCH_RESULT.value: (
        "⚽ Match Result",
        "{home_team} vs {away_team} ended {score}. Your prediction was {outcome}.",
    ),
    NotificationType.WALLET_ACTIVITY.value: (
        "💰 Wallet Activity",
        "{action}: {amount} {currency} — Balance updated.",
    ),
    NotificationType.VALIDATOR_REWARD.value: (
        "🏆 Validator Reward",
        "You earned {amount} VITCoin for your validator prediction on match #{match_id}.",
    ),
    NotificationType.SUBSCRIPTION_EXPIRY.value: (
        "⚠️ Subscription Expiring",
        "Your {plan} subscription expires in {days} day(s). Renew to keep access.",
    ),
    NotificationType.SYSTEM.value: (
        "🔔 System Notice",
        "{message}",
    ),
}


def render_template(ntype: str, context: dict) -> tuple[str, str]:
    title, body_tpl = TEMPLATES.get(ntype, ("🔔 Notification", "{message}"))
    try:
        body = body_tpl.format(**context)
    except KeyError:
        body = body_tpl
    return title, body


# ── Service ────────────────────────────────────────────────────────────────────

class NotificationService:

    # ── Core create ────────────────────────────────────────────────────────

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        ntype: NotificationType,
        context: dict,
        *,
        title: Optional[str] = None,
        body: Optional[str] = None,
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> Notification:
        rendered_title, rendered_body = render_template(ntype.value, context)
        notification = Notification(
            user_id=user_id,
            type=ntype,
            title=title or rendered_title,
            body=body or rendered_body,
            channel=channel,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Push over WebSocket immediately
        await notification_ws_manager.push(user_id, {
            "id":         notification.id,
            "type":       ntype.value,
            "title":      notification.title,
            "body":       notification.body,
            "is_read":    False,
            "created_at": notification.created_at.isoformat(),
        })

        return notification

    # ── Convenience methods ────────────────────────────────────────────────

    @classmethod
    async def notify_prediction(
        cls, db: AsyncSession, user_id: int, match: str, confidence: float
    ) -> Notification:
        return await cls.create(
            db, user_id, NotificationType.PREDICTION_ALERT,
            {"match": match, "confidence": round(confidence, 1)},
        )

    @classmethod
    async def notify_match_result(
        cls, db: AsyncSession, user_id: int,
        home_team: str, away_team: str, score: str, outcome: str
    ) -> Notification:
        return await cls.create(
            db, user_id, NotificationType.MATCH_RESULT,
            {"home_team": home_team, "away_team": away_team, "score": score, "outcome": outcome},
        )

    @classmethod
    async def notify_wallet(
        cls, db: AsyncSession, user_id: int,
        action: str, amount: str, currency: str
    ) -> Notification:
        return await cls.create(
            db, user_id, NotificationType.WALLET_ACTIVITY,
            {"action": action, "amount": amount, "currency": currency},
        )

    @classmethod
    async def notify_validator_reward(
        cls, db: AsyncSession, user_id: int, amount: str, match_id: int
    ) -> Notification:
        return await cls.create(
            db, user_id, NotificationType.VALIDATOR_REWARD,
            {"amount": amount, "match_id": match_id},
        )

    @classmethod
    async def notify_subscription_expiry(
        cls, db: AsyncSession, user_id: int, plan: str, days: int
    ) -> Notification:
        return await cls.create(
            db, user_id, NotificationType.SUBSCRIPTION_EXPIRY,
            {"plan": plan, "days": days},
        )

    @classmethod
    async def notify_system(
        cls, db: AsyncSession, user_id: int, message: str
    ) -> Notification:
        return await cls.create(
            db, user_id, NotificationType.SYSTEM,
            {"message": message},
        )

    # ── Queries ────────────────────────────────────────────────────────────

    @staticmethod
    async def get_for_user(
        db: AsyncSession, user_id: int, *, limit: int = 50, unread_only: bool = False
    ) -> list[Notification]:
        q = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            q = q.where(Notification.is_read == False)
        q = q.order_by(Notification.created_at.desc()).limit(limit)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def unread_count(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            select(func.count()).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> bool:
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notif = result.scalar_one_or_none()
        if not notif:
            return False
        notif.is_read = True
        await db.commit()
        return True

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        notifs = list(result.scalars().all())
        for n in notifs:
            n.is_read = True
        await db.commit()
        return len(notifs)

    # ── Preferences ───────────────────────────────────────────────────────

    @staticmethod
    async def get_or_create_prefs(
        db: AsyncSession, user_id: int
    ) -> NotificationPreference:
        result = await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        if not prefs:
            prefs = NotificationPreference(user_id=user_id)
            db.add(prefs)
            await db.commit()
            await db.refresh(prefs)
        return prefs

    @staticmethod
    async def update_prefs(
        db: AsyncSession, user_id: int, updates: dict
    ) -> NotificationPreference:
        result = await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        if not prefs:
            prefs = NotificationPreference(user_id=user_id)
            db.add(prefs)

        allowed = {
            "prediction_alerts", "match_results", "wallet_activity",
            "validator_rewards", "subscription_expiry",
            "email_enabled", "telegram_enabled", "in_app_enabled",
        }
        for k, v in updates.items():
            if k in allowed and isinstance(v, bool):
                setattr(prefs, k, v)

        await db.commit()
        await db.refresh(prefs)
        return prefs

    # ── Background: subscription expiry checker ────────────────────────────

    @staticmethod
    async def check_subscription_expiry(db: AsyncSession) -> None:
        """Warn users whose subscription expires within 3 days."""
        try:
            from app.db.models import UserSubscription
            now = datetime.utcnow()
            soon = now + timedelta(days=3)
            result = await db.execute(
                select(UserSubscription).where(
                    UserSubscription.is_active == True,
                    UserSubscription.end_date <= soon,
                    UserSubscription.end_date > now,
                )
            )
            subs = list(result.scalars().all())
            for sub in subs:
                days_left = max(0, (sub.end_date - now).days)
                await NotificationService.notify_subscription_expiry(
                    db,
                    user_id=sub.user_id,
                    plan=getattr(sub, "plan_name", "Premium"),
                    days=days_left,
                )
            if subs:
                logger.info(f"Subscription expiry: sent {len(subs)} warning(s)")
        except Exception as e:
            logger.warning(f"Subscription expiry check skipped: {e}")
