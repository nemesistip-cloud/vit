# app/services/telegram_service.py
"""Per-user Telegram DM notifications for VIT Network.

Uses the same TELEGRAM_BOT_TOKEN as the system TelegramAlert, but
sends to individual users' chat_ids instead of the admin channel.

User linking flow:
  1. User visits notification settings → clicks "Link Telegram"
  2. Frontend fetches GET /api/notifications/telegram/link-info
     → returns { bot_username, link_url, code }
  3. User clicks the deep-link (t.me/botname?start=CODE)
  4. Telegram sends the /start CODE message to the bot
  5. Our webhook POST /api/notifications/telegram/webhook processes it
     → finds the pending link code → stores chat_id on NotificationPreference
  6. User is now linked; DMs arrive for any enabled notification type
"""

import hashlib
import logging
import os
import secrets
from typing import Optional

import httpx
from app.config import APP_NAME, APP_SHORT_NAME

logger = logging.getLogger(__name__)

# In-memory store for pending link codes: { code: user_id }
# Codes expire after LINK_CODE_TTL_SECONDS.
import time as _time
_PENDING: dict[str, tuple[int, float]] = {}   # code → (user_id, expires_at)
LINK_CODE_TTL_SECONDS = 600  # 10 minutes


def generate_link_code(user_id: int) -> str:
    """Create a one-time link code for the given user."""
    code = secrets.token_urlsafe(16)
    _PENDING[code] = (user_id, _time.time() + LINK_CODE_TTL_SECONDS)
    # Prune expired entries while we're here
    now = _time.time()
    expired = [k for k, (_, exp) in _PENDING.items() if exp < now]
    for k in expired:
        _PENDING.pop(k, None)
    return code


def consume_link_code(code: str) -> Optional[int]:
    """
    Validate and consume a link code.
    Returns the user_id if valid, None otherwise.
    """
    entry = _PENDING.get(code)
    if not entry:
        return None
    user_id, expires_at = entry
    if _time.time() > expires_at:
        _PENDING.pop(code, None)
        return None
    _PENDING.pop(code, None)
    return user_id


def get_bot_token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def get_bot_username() -> str:
    """Return bot username from env or derive it from the token."""
    return os.getenv("TELEGRAM_BOT_USERNAME", "VITSportsBot")


async def send_user_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Send a Telegram DM to a specific user by their chat_id."""
    token = get_bot_token()
    if not token or not chat_id:
        logger.debug("Telegram DM skipped: no token or chat_id")
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id":                  chat_id,
                    "text":                     text,
                    "parse_mode":               parse_mode,
                    "disable_web_page_preview": True,
                },
            )
            if r.status_code == 200:
                logger.info(f"Telegram DM sent to chat_id={chat_id}")
                return True
            data = r.json()
            err = data.get("description", r.text[:120])
            logger.warning(f"Telegram DM error {r.status_code} for chat_id={chat_id}: {err}")
            return False
    except Exception as e:
        logger.warning(f"Telegram DM failed for chat_id={chat_id}: {e}")
        return False


_TYPE_ICONS = {
    "prediction_alert":    "🎯",
    "match_result":        "⚽",
    "wallet_activity":     "💰",
    "validator_reward":    "🏆",
    "subscription_expiry": "⚠️",
    "validator_status":    "🛡️",
    "system":              "🔔",
}


async def send_notification_telegram(
    chat_id: str,
    ntype: str,
    title: str,
    body: str,
) -> bool:
    """Send a per-user Telegram DM for a notification event."""
    icon = _TYPE_ICONS.get(ntype, "🔔")
    text = (
        f"{icon} <b>{title}</b>\n\n"
        f"{body}\n\n"
        f"<i>{APP_NAME}</i>"
    )
    return await send_user_message(chat_id, text)


async def send_test_telegram(chat_id: str) -> bool:
    """Send a test DM to verify the Telegram link is working."""
    return await send_user_message(
        chat_id,
        f"🔔 <b>Test Notification — {APP_SHORT_NAME}</b>\n\n"
        "Your Telegram notifications are working correctly.\n\n"
        f"<i>{APP_NAME}</i>",
    )


async def process_webhook_update(update: dict) -> Optional[int]:
    """
    Parse a Telegram webhook update.
    If the message is /start {code}, links the account.
    Returns the user_id that was linked, or None.
    """
    message = update.get("message") or update.get("channel_post")
    if not message:
        return None

    text = (message.get("text") or "").strip()
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))

    if not text.startswith("/start"):
        return None

    parts = text.split()
    code = parts[1] if len(parts) > 1 else None

    if not code:
        # No code — welcome message
        await send_user_message(
            chat_id,
            f"👋 <b>Welcome to {APP_NAME}!</b>\n\n"
            f"To link your account, visit your notification settings in the {APP_SHORT_NAME} app "
            "and click <b>Link Telegram</b> to get your personalised link.",
        )
        return None

    user_id = consume_link_code(code)
    if not user_id:
        await send_user_message(
            chat_id,
            "❌ <b>Link code expired or invalid.</b>\n\n"
            f"Please generate a new link from your {APP_SHORT_NAME} notification settings.",
        )
        return None

    # Return user_id + chat_id — the caller stores them
    # Attach chat_id to update so the route can access it
    update["_resolved_user_id"] = user_id
    update["_resolved_chat_id"] = chat_id

    await send_user_message(
        chat_id,
        "✅ <b>Telegram linked successfully!</b>\n\n"
        f"You'll now receive {APP_SHORT_NAME} notifications directly here.\n\n"
        f"<i>{APP_NAME}</i>",
    )
    return user_id
