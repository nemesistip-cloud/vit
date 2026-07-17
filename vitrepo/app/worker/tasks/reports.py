"""app/worker/tasks/reports.py — Daily/weekly reporting Celery tasks."""
from __future__ import annotations
import asyncio, json, logging, os, time
from celery.utils.log import get_task_logger
from app.worker.celery_app import celery

logger = get_task_logger(__name__)


@celery.task(name="reports.daily_summary", max_retries=2, default_retry_delay=300,
             soft_time_limit=300, time_limit=420)
def daily_summary():
    """Generate daily platform summary and send via Telegram."""
    return asyncio.run(_run_daily())


async def _run_daily():
    from datetime import datetime, timezone, timedelta
    from app.db.database import AsyncSessionLocal
    from app.db.models import Match, Prediction, User
    from sqlalchemy import select, func, and_

    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).replace(tzinfo=None)

    async with AsyncSessionLocal() as db:
        preds_24h = (await db.execute(
            select(func.count(Prediction.id))
            .where(Prediction.timestamp >= yesterday)
        )).scalar() or 0

        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

        settled = (await db.execute(
            select(func.count(Match.id)).where(Match.actual_outcome.isnot(None))
        )).scalar() or 0

    summary = {
        "date": now.strftime("%Y-%m-%d"), "predictions_24h": preds_24h,
        "total_users": total_users, "settled_matches": settled,
    }
    msg = (
        f"📊 *VIT Daily — {summary['date']}*\n"
        f"Predictions (24h): {preds_24h}\n"
        f"Total Users: {total_users}\n"
        f"Settled Matches: {settled}"
    )
    try:
        from app.services.alerts import TelegramAlert
        await TelegramAlert(
            os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            os.environ.get("TELEGRAM_CHAT_ID", ""),
        ).send(msg)
    except Exception as exc:
        logger.warning("[reports.daily] telegram failed: %s", exc)

    logger.info("[reports.daily] %s", json.dumps(summary))
    return summary


@celery.task(name="reports.weekly_model_accuracy", max_retries=1,
             default_retry_delay=600, soft_time_limit=300, time_limit=420)
def weekly_model_accuracy():
    """Compute 7-day prediction accuracy and push to Redis."""
    return asyncio.run(_run_weekly_acc())


async def _run_weekly_acc():
    from datetime import datetime, timezone, timedelta
    from app.db.database import AsyncSessionLocal
    from app.db.models import Match, Prediction
    from sqlalchemy import select, and_

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).replace(tzinfo=None)
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Prediction.home_prob, Prediction.draw_prob,
                   Prediction.away_prob, Match.actual_outcome)
            .join(Match, Match.id == Prediction.match_id)
            .where(and_(Match.actual_outcome.isnot(None),
                        Prediction.timestamp >= cutoff))
            .limit(2000)
        )).all()

    if not rows:
        return {"status": "no_data"}

    correct = sum(
        1 for hp, dp, ap, outcome in rows
        if max(("home",float(hp or 0)),("draw",float(dp or 0)),
               ("away",float(ap or 0)),key=lambda x:x[1])[0] == outcome
    )
    acc = round(correct / len(rows), 4)
    result = {"accuracy_7d": acc, "sample_size": len(rows), "ts": time.time()}
    try:
        import redis as _r
        r = _r.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        r.setex("ml:accuracy:7d", 604800, json.dumps(result))
        r.close()
    except Exception: pass
    logger.info("[reports.weekly] acc=%.2f%% n=%d", acc * 100, len(rows))
    return result
