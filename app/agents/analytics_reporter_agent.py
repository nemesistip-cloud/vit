"""app/agents/analytics_reporter_agent.py  — Item 6: Analytics Narrative Reporter

Runs every 7 days. Pulls the past 7 days of platform analytics, feeds
them to Gemini, and generates a plain-English performance report with:
  - Revenue trends (subscriptions, VITCoin, marketplace fees)
  - Model accuracy trends
  - User engagement and retention signals
  - Anomaly flags
  - Three recommended actions

Report is sent to the admin Telegram channel and stored as an AgentInsight.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict


from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)


async def _gather_analytics(db_session) -> dict:
    """Pull 7-day analytics summary from the database."""
    from sqlalchemy import select, func
    from app.db.models import Match, Prediction, User, AIPrediction
    from app.modules.wallet.models import WalletTransaction, WalletUserSubscription, WithdrawalRequest

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    stats = {}

    try:
        # Active users (7d)
        stats["active_users_7d"] = (await db_session.execute(
            select(func.count(func.distinct(WalletTransaction.user_id)))
            .where(WalletTransaction.created_at >= week_ago)
        )).scalar() or 0
    except Exception:
        stats["active_users_7d"] = 0

    try:
        # New subscriptions
        stats["new_subscriptions_7d"] = (await db_session.execute(
            select(func.count(WalletUserSubscription.id))
            .where(WalletUserSubscription.created_at >= week_ago)
        )).scalar() or 0
    except Exception:
        stats["new_subscriptions_7d"] = 0

    try:
        # Predictions made
        stats["predictions_7d"] = (await db_session.execute(
            select(func.count(Prediction.id))
            .where(Prediction.created_at >= week_ago)
        )).scalar() or 0
    except Exception:
        stats["predictions_7d"] = 0

    try:
        # AI predictions ingested
        stats["ai_sources_ingested_7d"] = (await db_session.execute(
            select(func.count(AIPrediction.id))
            .where(AIPrediction.timestamp >= week_ago)
        )).scalar() or 0
    except Exception:
        stats["ai_sources_ingested_7d"] = 0

    try:
        # Matches in DB
        stats["total_matches"] = (await db_session.execute(
            select(func.count(Match.id))
        )).scalar() or 0
    except Exception:
        stats["total_matches"] = 0

    try:
        # Pending withdrawals
        stats["pending_withdrawals"] = (await db_session.execute(
            select(func.count(WithdrawalRequest.id))
            .where(WithdrawalRequest.status == "pending")
        )).scalar() or 0
    except Exception:
        stats["pending_withdrawals"] = 0

    try:
        # Total users
        stats["total_users"] = (await db_session.execute(
            select(func.count(User.id))
        )).scalar() or 0
    except Exception:
        stats["total_users"] = 0

    return stats


def _build_report_prompt(stats: dict, report_date: str) -> str:
    return (
        f"You are the analytics director for VIT Sports Intelligence Network, a professional "
        f"sports prediction and betting analytics SaaS platform.\n\n"
        f"Weekly Performance Report — Week ending {report_date}\n\n"
        f"Platform Metrics (last 7 days):\n"
        f"  Active users: {stats.get('active_users_7d', 0)}\n"
        f"  New subscriptions: {stats.get('new_subscriptions_7d', 0)}\n"
        f"  Predictions generated: {stats.get('predictions_7d', 0)}\n"
        f"  AI sources ingested: {stats.get('ai_sources_ingested_7d', 0)}\n"
        f"  Matches in database: {stats.get('total_matches', 0)}\n"
        f"  Pending withdrawals: {stats.get('pending_withdrawals', 0)}\n"
        f"  Total registered users: {stats.get('total_users', 0)}\n\n"
        f"Write a concise executive summary covering:\n"
        f"1. Platform health overview (2-3 sentences)\n"
        f"2. Key wins this week\n"
        f"3. Concerns or anomalies to watch\n"
        f"4. Three specific recommended actions for next week\n\n"
        f"Keep it under 400 words. Be direct and specific. Use emoji sparingly."
    )


class AnalyticsReporterAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="analytics-reporter",
            interval_seconds=7 * 24 * 60 * 60,   # weekly
            initial_delay_seconds=600,             # 10 min after startup
        )

    async def run_cycle(self) -> Dict[str, Any]:

        from app.db.database import AsyncSessionLocal
        from app.db.models import AgentInsight
        from app.services.alerts import TelegramAlert, AlertPriority

        now = datetime.now(timezone.utc)
        report_date = now.strftime("%Y-%m-%d")

        async with AsyncSessionLocal() as db:
            stats = await _gather_analytics(db)

        prompt = _build_report_prompt(stats, report_date)
        report = await call_ai(prompt, max_tokens=900)

        if not report:
            return {"skipped": True, "reason": "Gemini returned no response"}

        # Store as AgentInsight
        async with AsyncSessionLocal() as db:
            insight = AgentInsight(
                agent_name="analytics-reporter",
                insight_type="weekly_report",
                ai_provider="gemini",
                content=report[:2000],
                meta={"stats": stats, "report_date": report_date},
                confidence=0.8,
            )
            db.add(insight)
            await db.commit()

        # Send to Telegram
        try:
            tg = TelegramAlert()
            header = f"<b>📊 VIT Weekly Analytics — {report_date}</b>\n{'━'*22}\n\n"
            await tg.send_message(header + report[:3500], AlertPriority.LOW)
        except Exception as te:
            logger.warning("[analytics-reporter] Telegram failed: %s", te)

        logger.info("[analytics-reporter] weekly report generated and sent")
        return {"report_date": report_date, "stats": stats, "report_length": len(report)}
