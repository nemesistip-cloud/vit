import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import Match, Prediction
from app.services.telegram_service import send_user_message
from app.config import TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

async def send_daily_digest():
    """Send a high-confidence signal digest to the main Telegram channel."""
    if not TELEGRAM_CHAT_ID:
        logger.warning("Telegram digest skipped: TELEGRAM_CHAT_ID not configured")
        return

    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            lookahead = now + asyncio.timedelta(days=1)

            stmt = (
                select(Match, Prediction)
                .join(Prediction, Match.id == Prediction.match_id)
                .where(Match.kickoff_time >= now)
                .where(Match.kickoff_time <= lookahead)
                .where(Prediction.confidence >= 0.75)
                .order_by(Prediction.confidence.desc())
                .limit(5)
            )
            res = await db.execute(stmt)
            top_picks = res.all()

            if not top_picks:
                return

            msg = "📊 <b>VIT Daily Signal Digest</b>\n\n"
            msg += f"Top high-confidence picks for {now.strftime('%d %b')}:\n\n"

            for match, pred in top_picks:
                side = (pred.bet_side or "home").upper()
                msg += f"⚽ <b>{match.home_team} vs {match.away_team}</b>\n"
                msg += f"🎯 Pick: {side} | Conf: {pred.confidence*100:.0f}%\n\n"

            msg += "<i>Analyze full insights in the VIT Super App.</i>"

            await send_user_message(TELEGRAM_CHAT_ID, msg)
            logger.info("Daily Telegram digest sent")

    except Exception as e:
        logger.error(f"Error in Telegram digest: {e}")

async def telegram_digest_worker():
    """Worker to send digest once per day."""
    while True:
        # Send at 9 AM UTC
        now = datetime.now(timezone.utc)
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= target:
            target += asyncio.timedelta(days=1)

        sleep_seconds = (target - now).total_seconds()
        await asyncio.sleep(sleep_seconds)
        await send_daily_digest()

def start_telegram_digest():
    asyncio.create_task(telegram_digest_worker())
