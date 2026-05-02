"""app/agents/revenue_optimizer_agent.py  — Item 10: Revenue Optimizer

Runs daily. Analyzes subscription revenue, churn signals, and marketplace
activity, then calls Gemini to recommend pricing adjustments and growth
actions. Sends recommendations to the admin Telegram channel.

Does NOT auto-apply pricing changes — recommendations only, for admin
review. (Auto-apply can be enabled via REVENUE_AUTO_APPLY=true env var.)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

_GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]


async def _call_gemini(prompt: str, api_key: str) -> str | None:
    for model in _GEMINI_MODELS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 700},
                })
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                continue
            return None
        except Exception as e:
            logger.warning("[revenue-optimizer] Gemini error: %s", e)
            return None
    return None


async def _gather_revenue_metrics(db) -> dict:
    from sqlalchemy import select, func
    from app.modules.wallet.models import (
        WalletTransaction, WalletUserSubscription,
        WithdrawalRequest, WalletSubscriptionPlan,
    )
    from app.modules.marketplace.models import AIModelListing, ModelUsageLog

    now = datetime.now(timezone.utc)
    day7 = now - timedelta(days=7)
    day30 = now - timedelta(days=30)
    metrics = {}

    try:
        metrics["active_subs_7d"] = (await db.execute(
            select(func.count(WalletUserSubscription.id))
            .where(WalletUserSubscription.created_at >= day7)
        )).scalar() or 0
    except Exception:
        metrics["active_subs_7d"] = 0

    try:
        metrics["expired_subs_7d"] = (await db.execute(
            select(func.count(WalletUserSubscription.id))
            .where(
                WalletUserSubscription.expires_at >= day7,
                WalletUserSubscription.expires_at <= now,
            )
        )).scalar() or 0
    except Exception:
        metrics["expired_subs_7d"] = 0

    try:
        metrics["marketplace_listings_active"] = (await db.execute(
            select(func.count(AIModelListing.id))
            .where(AIModelListing.status == "approved")
        )).scalar() or 0
    except Exception:
        metrics["marketplace_listings_active"] = 0

    try:
        metrics["marketplace_usage_7d"] = (await db.execute(
            select(func.count(ModelUsageLog.id))
            .where(ModelUsageLog.called_at >= day7)
        )).scalar() or 0
    except Exception:
        metrics["marketplace_usage_7d"] = 0

    try:
        metrics["pending_withdrawals"] = (await db.execute(
            select(func.count(WithdrawalRequest.id))
            .where(WithdrawalRequest.status == "pending")
        )).scalar() or 0
    except Exception:
        metrics["pending_withdrawals"] = 0

    try:
        plans_res = await db.execute(select(WalletSubscriptionPlan).where(WalletSubscriptionPlan.is_active == True))
        plans = plans_res.scalars().all()
        metrics["plans"] = [
            {"name": p.name, "price_usd": float(p.price_usd), "duration_days": p.duration_days}
            for p in plans
        ]
    except Exception:
        metrics["plans"] = []

    return metrics


def _build_optimizer_prompt(metrics: dict, date: str) -> str:
    churn_rate = 0.0
    new = metrics.get("active_subs_7d", 0)
    expired = metrics.get("expired_subs_7d", 0)
    if new > 0:
        churn_rate = expired / max(new + expired, 1)

    plans_str = "\n".join(
        f"  - {p['name']}: ${p['price_usd']:.2f}/{p['duration_days']}d"
        for p in metrics.get("plans", [])
    ) or "  (no plans found)"

    return (
        f"You are a SaaS revenue strategist. Analyze this sports prediction platform's metrics.\n\n"
        f"Report date: {date}\n\n"
        f"Metrics (last 7 days):\n"
        f"  New subscriptions: {metrics.get('active_subs_7d', 0)}\n"
        f"  Expired/churned: {metrics.get('expired_subs_7d', 0)}\n"
        f"  Churn rate: {churn_rate:.1%}\n"
        f"  Marketplace listings (active): {metrics.get('marketplace_listings_active', 0)}\n"
        f"  Marketplace API calls: {metrics.get('marketplace_usage_7d', 0)}\n"
        f"  Pending withdrawals: {metrics.get('pending_withdrawals', 0)}\n\n"
        f"Current pricing:\n{plans_str}\n\n"
        f"Provide:\n"
        f"1. Revenue health assessment (2 sentences)\n"
        f"2. Top 3 specific pricing or growth recommendations\n"
        f"3. One warning if any metric looks alarming\n\n"
        f"Be direct and actionable. Max 300 words."
    )


class RevenueOptimizerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="revenue-optimizer",
            interval_seconds=24 * 60 * 60,
            initial_delay_seconds=400,
        )

    async def run_cycle(self) -> Dict[str, Any]:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return {"skipped": True, "reason": "GEMINI_API_KEY not set"}

        from app.db.database import AsyncSessionLocal
        from app.db.models import AgentInsight
        from app.services.alerts import TelegramAlert, AlertPriority

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        async with AsyncSessionLocal() as db:
            metrics = await _gather_revenue_metrics(db)

        prompt = _build_optimizer_prompt(metrics, date_str)
        report = await _call_gemini(prompt, api_key)

        if not report:
            return {"skipped": True, "reason": "no Gemini response"}

        async with AsyncSessionLocal() as db:
            insight = AgentInsight(
                agent_name="revenue-optimizer",
                insight_type="revenue_report",
                ai_provider="gemini",
                content=report[:2000],
                meta={"metrics": metrics, "date": date_str},
                confidence=0.75,
            )
            db.add(insight)
            await db.commit()

        try:
            tg = TelegramAlert()
            await tg.send_message(
                f"<b>💰 Revenue Optimizer Report — {date_str}</b>\n{'━'*22}\n\n{report[:2500]}",
                AlertPriority.LOW,
            )
        except Exception as te:
            logger.warning("[revenue-optimizer] Telegram error: %s", te)

        logger.info("[revenue-optimizer] daily report sent")
        return {"date": date_str, "metrics": metrics, "report_length": len(report)}
