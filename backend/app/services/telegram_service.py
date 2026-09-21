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
import secrets
import json
import os
from decimal import Decimal
from typing import Optional, Dict, Any, List
import time as _time

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME

import httpx

logger = logging.getLogger(__name__)

# In-memory store for pending link codes: { code: user_id }
# Codes expire after LINK_CODE_TTL_SECONDS.
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
    return TELEGRAM_BOT_TOKEN


def get_bot_username() -> str:
    """Return bot username from env or derive it from the token."""
    return TELEGRAM_BOT_USERNAME


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
        f"<i>VIT Sports Analytics Network</i>"
    )
    return await send_user_message(chat_id, text)


async def send_test_telegram(chat_id: str) -> bool:
    """Send a test DM to verify the Telegram link is working."""
    return await send_user_message(
        chat_id,
        "🔔 <b>Test Notification — VIT Network</b>\n\n"
        "Your Telegram notifications are working correctly.\n\n"
        "<i>VIT Sports Analytics Network</i>",
    )


async def _cmd_top5(chat_id: str) -> None:
    """Send the top 5 high-confidence upcoming picks."""
    try:
        from app.db.database import AsyncSessionLocal
        from app.db.models import Match, Prediction
        from sqlalchemy import select, func
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=7)

        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(Match, Prediction)
                .join(Prediction, Prediction.match_id == Match.id)
                .where(
                    Match.kickoff_time >= now,
                    Match.kickoff_time <= cutoff,
                    Match.actual_outcome.is_(None),
                    Prediction.confidence >= 0.60,
                )
                .order_by(Prediction.confidence.desc())
                .limit(5)
            )
            rows = res.all()

        if not rows:
            await send_user_message(chat_id, "📭 No high-confidence picks found for the next 7 days yet. Check back soon!")
            return

        lines = ["🏆 <b>Top 5 Picks (Next 7 Days)</b>\n"]
        for i, (match, pred) in enumerate(rows, 1):
            ko = match.kickoff_time.strftime("%d %b %H:%M") if match.kickoff_time else "TBD"
            side = (pred.bet_side or "home").upper()
            conf = f"{(pred.confidence or 0)*100:.0f}%"
            edge = f"{(pred.raw_edge or 0)*100:+.1f}%"
            lines.append(
                f"{i}. <b>{match.home_team} v {match.away_team}</b>\n"
                f"   🎯 <b>{side}</b> · {conf} conf · {edge} edge\n"
                f"   📅 {ko}\n"
            )

        await send_user_message(chat_id, "\n".join(lines) + "\n<i>VIT Sports Analytics</i>")
    except Exception as exc:
        logger.warning("[tg-cmd] top5 error: %s", exc)
        await send_user_message(chat_id, "⚠️ Could not fetch picks right now. Try again shortly.")


async def _cmd_stats(chat_id: str) -> None:
    """Send platform performance stats."""
    try:
        from app.db.database import AsyncSessionLocal
        from app.db.models import Match, Prediction
        from sqlalchemy import select, func
        from datetime import datetime, timezone, timedelta

        cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)

        async with AsyncSessionLocal() as db:
            total_matches = (await db.execute(select(func.count(Match.id)))).scalar() or 0
            total_preds = (await db.execute(select(func.count(Prediction.id)))).scalar() or 0
            settled_preds = (await db.execute(
                select(func.count(Prediction.id)).where(Prediction.was_correct.isnot(None))
            )).scalar() or 0
            correct_preds = (await db.execute(
                select(func.count(Prediction.id)).where(Prediction.was_correct == True)
            )).scalar() or 0

        acc = f"{correct_preds/settled_preds*100:.1f}%" if settled_preds else "N/A"
        msg = (
            "📊 <b>VIT Platform Stats</b>\n\n"
            f"⚽ <b>Total Matches:</b> {total_matches:,}\n"
            f"🎯 <b>Total Predictions:</b> {total_preds:,}\n"
            f"✅ <b>Settled Predictions:</b> {settled_preds:,}\n"
            f"📈 <b>Overall Accuracy:</b> {acc}\n\n"
            "<i>VIT Sports Analytics Network</i>"
        )
        await send_user_message(chat_id, msg)
    except Exception as exc:
        logger.warning("[tg-cmd] stats error: %s", exc)
        await send_user_message(chat_id, "⚠️ Could not fetch stats right now. Try again shortly.")


async def _cmd_predict(chat_id: str, text: str) -> None:
    """Handle /predict <team1> vs <team2> by looking up matching fixtures."""
    try:
        # Parse the teams from the command text
        parts = text.split(None, 1)
        query = parts[1].strip() if len(parts) > 1 else ""

        if not query:
            await send_user_message(
                chat_id,
                "ℹ️ Usage: <code>/predict &lt;team1&gt; vs &lt;team2&gt;</code>\n"
                "Example: <code>/predict Arsenal vs Chelsea</code>",
            )
            return

        # Normalise "vs" separators
        sep = " vs " if " vs " in query.lower() else (" v " if " v " in query.lower() else None)
        if sep:
            home_q, _, away_q = query.lower().partition(sep.lower())
        else:
            home_q, away_q = query.lower(), ""

        from app.db.database import AsyncSessionLocal
        from app.db.models import Match, Prediction
        from sqlalchemy import select, func
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            stmt = (
                select(Match, Prediction)
                .outerjoin(Prediction, Prediction.match_id == Match.id)
                .where(Match.kickoff_time >= now)
            )
            if home_q:
                stmt = stmt.where(func.lower(Match.home_team).contains(home_q.strip()))
            if away_q:
                stmt = stmt.where(func.lower(Match.away_team).contains(away_q.strip()))
            stmt = stmt.order_by(Match.kickoff_time.asc()).limit(1)
            res = await db.execute(stmt)
            row = res.first()

        if not row:
            await send_user_message(chat_id, f"❓ No upcoming match found for <b>{query}</b>. Check the spelling or browse /top5.")
            return

        match, pred = row
        ko = match.kickoff_time.strftime("%d %b %H:%M UTC") if match.kickoff_time else "TBD"
        if pred:
            side = (pred.bet_side or "home").upper()
            conf = f"{(pred.confidence or 0)*100:.0f}%"
            edge = f"{(pred.raw_edge or 0)*100:+.1f}%"
            rec = (
                f"🎯 <b>Recommendation: {side}</b>\n"
                f"📊 Confidence: {conf}  |  Edge: {edge}\n"
                f"🏠 Home: {(pred.home_prob or 0)*100:.0f}%  "
                f"🤝 Draw: {(pred.draw_prob or 0)*100:.0f}%  "
                f"✈️ Away: {(pred.away_prob or 0)*100:.0f}%"
            )
        else:
            rec = "⏳ Prediction pending — check back shortly."

        msg = (
            f"⚽ <b>{match.home_team} vs {match.away_team}</b>\n"
            f"🏆 {match.league or 'League TBD'}  |  📅 {ko}\n\n"
            f"{rec}\n\n<i>VIT Sports Analytics Network</i>"
        )
        await send_user_message(chat_id, msg)
    except Exception as exc:
        logger.warning("[tg-cmd] predict error: %s", exc)
        await send_user_message(chat_id, "⚠️ Could not process prediction request. Try again shortly.")

async def create_stars_invoice(user_id: int, stars_amount: int) -> Optional[str]:
    """
    Create a Telegram Stars invoice link.
    stars_amount is the number of Stars.
    """
    token = get_bot_token()
    if not token:
        return None

    payload = {
        "title": f"{stars_amount} Telegram Stars for VITCoin",
        "description": f"Purchase {stars_amount} Stars to convert into VITCoin on the VIT Network.",
        "payload": json.dumps({"user_id": user_id, "stars": stars_amount, "type": "stars_purchase"}),
        "provider_token": "", # Empty for Telegram Stars
        "currency": "XTR",     # XTR is the currency code for Telegram Stars
        "prices": [{"label": "Stars", "amount": stars_amount}],
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{token}/createInvoiceLink",
                json=payload,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    return data.get("result")
            logger.error(f"Failed to create invoice link: {r.text}")
            return None
    except Exception as e:
        logger.error(f"Error creating invoice link: {e}")
        return None

async def process_webhook_update(update: dict) -> Optional[int]:
    """
    Parse a Telegram webhook update.
    If the message is /start {code}, links the account.
    Returns the user_id that was linked, or None.
    """
    message = update.get("message") or update.get("channel_post")

    # ── Payment handling ──────────────────────────────────────────────────
    if "pre_checkout_query" in update:
        query = update["pre_checkout_query"]
        token = get_bot_token()
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/answerPreCheckoutQuery",
                json={"pre_checkout_query_id": query["id"], "ok": True},
            )
        return None

    if message and "successful_payment" in message:
        payment = message["successful_payment"]
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        payload_str = payment.get("invoice_payload")
        if payload_str:
            try:
                payload = json.loads(payload_str)
                if payload.get("type") == "stars_purchase":
                    user_id = payload.get("user_id")
                    stars = payload.get("stars")
                    vit_amount = Decimal(str(stars)) * Decimal("0.2")

                    from app.db.database import AsyncSessionLocal
                    from app.modules.wallet.services import WalletService
                    from app.modules.wallet.models import Currency

                    async with AsyncSessionLocal() as db:
                        ws = WalletService(db)
                        wallet = await ws.get_or_create_wallet(user_id)
                        await ws.credit(
                            wallet.id, user_id, Currency.VITCOIN, vit_amount,
                            "deposit", reference=f"STARS_{message['message_id']}",
                            metadata={"stars": stars, "provider": "telegram_stars"}
                        )
                        await db.commit()

                    await send_user_message(
                        chat_id,
                        f"✅ <b>Payment Successful!</b>\n\n"
                        f"You purchased {stars} Stars and received <b>{vit_amount} VITCoin</b>.\n"
                        f"Your balance has been updated."
                    )
            except Exception as e:
                logger.error(f"Error processing successful payment: {e}")
        return None

    if not message:
        return None

    text = (message.get("text") or "").strip()
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))

    # ── Bot commands ──────────────────────────────────────────────────────
    if text.startswith("/top5") or text.startswith("/top"):
        await _cmd_top5(chat_id)
        return None

    if text.startswith("/stats"):
        await _cmd_stats(chat_id)
        return None

    if text.startswith("/predict"):
        await _cmd_predict(chat_id, text)
        return None

    if text.startswith("/help"):
        await send_user_message(
            chat_id,
            "🤖 <b>VIT Bot Commands</b>\n\n"
            "• /top5 — Today's top 5 high-confidence picks\n"
            "• /stats — Platform performance stats\n"
            "• /predict &lt;team1&gt; vs &lt;team2&gt; — Quick prediction request\n"
            "• /help — Show this message\n\n"
            "<i>VIT Sports Analytics Network</i>",
        )
        return None

    if not text.startswith("/start"):
        return None

    parts = text.split()
    code = parts[1] if len(parts) > 1 else None

    if not code:
        # If no code, suggest opening the Mini App
        pub_url = (os.getenv("PUBLIC_APP_URL") or os.getenv("REPLIT_DEV_DOMAIN") or "").rstrip("/")
        if not pub_url.startswith("http") and pub_url: pub_url = f"https://{pub_url}"

        keyboard = {"inline_keyboard": [[{"text": "🚀 Open VIT Mini App", "web_app": {"url": pub_url}}]]} if pub_url else None

        token = get_bot_token()
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        "👋 <b>Welcome to VIT Sports Analytics!</b>\n\n"
                        "The VIT Mini App is now available! Tap the button below to launch it directly in Telegram.\n\n"
                        "To link your external account, visit your notification settings in the VIT web app."
                    ),
                    "parse_mode": "HTML",
                    "reply_markup": keyboard
                }
            )
        return None

    user_id = consume_link_code(code)
    if not user_id:
        await send_user_message(
            chat_id,
            "❌ <b>Link code expired or invalid.</b>\n\n"
            "Please generate a new link from your VIT notification settings.",
        )
        return None

    # Return user_id + chat_id — the caller stores them
    # Attach chat_id to update so the route can access it
    update["_resolved_user_id"] = user_id
    update["_resolved_chat_id"] = chat_id

    await send_user_message(
        chat_id,
        "✅ <b>Telegram linked successfully!</b>\n\n"
        "You'll now receive VIT notifications directly here.\n\n"
        "<i>VIT Sports Analytics Network</i>",
    )
    return user_id
