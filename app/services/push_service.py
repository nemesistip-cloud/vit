import json
import logging
from typing import Optional, List
from pywebpush import webpush, WebPushException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_env
from app.modules.notifications.models import PushSubscription

logger = logging.getLogger(__name__)

VAPID_PUBLIC_KEY = get_env("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = get_env("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS = {"sub": "mailto:support@vit.network"}

class PushService:
    @staticmethod
    async def send_push_notification(subscription: PushSubscription, title: str, body: str, data: Optional[dict] = None):
        """Send a Web Push notification to a specific subscription."""
        if not VAPID_PRIVATE_KEY:
            logger.warning("Push failed: VAPID_PRIVATE_KEY not configured")
            return False

        try:
            message = {
                "title": title,
                "body": body,
                "data": data or {}
            }

            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth
                    }
                },
                data=json.dumps(message),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
            return True
        except WebPushException as ex:
            logger.warning(f"WebPush error: {ex}")
            # If 410 Gone, we should probably delete the subscription
            return False
        except Exception as e:
            logger.error(f"Failed to send push: {e}")
            return False

    @staticmethod
    async def notify_user(db: AsyncSession, user_id: int, title: str, body: str, data: Optional[dict] = None):
        """Send push notifications to all active subscriptions of a user."""
        stmt = select(PushSubscription).where(PushSubscription.user_id == user_id)
        res = await db.execute(stmt)
        subs = res.scalars().all()

        results = []
        for sub in subs:
            results.append(await PushService.send_push_notification(sub, title, body, data))

        return any(results) if results else False

async def broadcast_push_notification(db: AsyncSession, title: str, body: str, data: Optional[dict] = None):
    """Send push notifications to all registered subscribers."""
    stmt = select(PushSubscription)
    res = await db.execute(stmt)
    subs = res.scalars().all()

    for sub in subs:
        await PushService.send_push_notification(sub, title, body, data)
