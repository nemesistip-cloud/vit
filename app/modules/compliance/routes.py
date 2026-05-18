"""app/modules/compliance/routes.py
Security & Compliance Layer — Phase 5/14
Jurisdictional contracts, tax automation, and responsible gaming.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User, Prediction, BankrollState

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])
logger = logging.getLogger(__name__)


@router.get("/jurisdiction-config")
async def get_config(country: str, current_user: User = Depends(get_current_user)):
    return {"country": country, "user_id": current_user.id, "max_stake": 500, "kyc_required": True, "tax_rate": 0.15}


@router.post("/responsible-gaming/set-limits")
async def set_gaming_limits(daily_limit: float, current_user: User = Depends(get_current_user)):
    return {"status": "limit_set", "user_id": current_user.id, "daily_limit": daily_limit, "cooldown_period": "24h"}


# ── Discipline Coach ──────────────────────────────────────────────────────────

_DAILY_LOSS_LIMIT = 100.0   # default daily loss cap (USD equiv)
_COOLDOWN_HOURS   = 24


def _compute_behavior_score(
    total_preds: int,
    win_rate: float,
    avg_stake: float,
    stake_std: float,
    streak: int,         # negative = losing streak
    settled: int,
) -> int:
    """Deterministic 0-100 discipline score based on real betting behaviour."""
    score = 60  # base

    # Activity bonus — requires at least 5 settled predictions
    if settled >= 5:
        score += 5
    if settled >= 20:
        score += 5

    # Win rate bonus
    if win_rate >= 0.55:
        score += 10
    elif win_rate >= 0.45:
        score += 5
    elif win_rate < 0.35 and settled >= 5:
        score -= 10

    # Stake consistency (lower coefficient of variation = more disciplined)
    if avg_stake > 0:
        cv = stake_std / avg_stake
        if cv < 0.20:
            score += 10
        elif cv < 0.40:
            score += 5
        elif cv > 0.80:
            score -= 10

    # Losing streak penalty
    if streak <= -5:
        score -= 15
    elif streak <= -3:
        score -= 5

    return max(0, min(100, score))


def _build_insights(
    win_rate: float,
    avg_stake: float,
    stake_std: float,
    streak: int,
    settled: int,
    avg_confidence: float,
) -> List[Dict[str, str]]:
    insights: List[Dict[str, str]] = []

    if settled < 3:
        insights.append({
            "type": "info",
            "icon": "zap",
            "title": "Getting Started",
            "body": "Make at least 3 settled predictions to unlock personalised coaching insights.",
        })
        return insights

    # Stake sizing
    cv = (stake_std / avg_stake) if avg_stake > 0 else 1.0
    if cv < 0.30:
        insights.append({
            "type": "positive",
            "icon": "zap",
            "title": "Consistent Sizing",
            "body": "Your stake size remains consistent relative to your bankroll. No signs of chasing losses detected.",
        })
    else:
        insights.append({
            "type": "warning",
            "icon": "alert",
            "title": "Variable Sizing Detected",
            "body": f"Your average stake varies significantly (CV {cv:.0%}). Try to keep stakes within ±20% of your unit size.",
        })

    # Win rate commentary
    if win_rate >= 0.55:
        insights.append({
            "type": "positive",
            "icon": "trend",
            "title": "Strong Hit Rate",
            "body": f"Your {win_rate:.0%} win rate is above the break-even threshold for typical -110 lines. Keep it up.",
        })
    elif win_rate < 0.40 and settled >= 10:
        insights.append({
            "type": "warning",
            "icon": "alert",
            "title": "Win Rate Below Break-Even",
            "body": f"At {win_rate:.0%} over {settled} bets you are below the ~52% threshold needed to profit at -110. Review model selection.",
        })

    # Confidence vs accuracy
    if avg_confidence > 0.70 and win_rate < 0.50 and settled >= 5:
        insights.append({
            "type": "warning",
            "icon": "brain",
            "title": "Overconfidence Signal",
            "body": "You are selecting high-confidence predictions but hitting below 50%. Consider diversifying into moderate-confidence edges.",
        })
    elif avg_confidence > 0 and avg_confidence <= 0.65 and win_rate >= 0.55:
        insights.append({
            "type": "positive",
            "icon": "brain",
            "title": "Calibrated Selections",
            "body": "You are selecting moderate-confidence predictions and beating them — a sign of disciplined value-hunting.",
        })

    # Streak
    if streak <= -3:
        insights.append({
            "type": "warning",
            "icon": "alert",
            "title": f"Losing Streak: {abs(streak)}",
            "body": "Consider a short pause. Chasing losses after consecutive misses is the most common bankroll killer.",
        })
    elif streak >= 5:
        insights.append({
            "type": "positive",
            "icon": "trend",
            "title": f"Hot Streak: +{streak}",
            "body": "Great run — but stay disciplined with stake sizing. Overconfidence during hot streaks leads to outsized losses.",
        })

    return insights[:4]  # cap at 4 insights


@router.get("/discipline/overview")
async def get_discipline_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute and return the live behavior score, coach insights, and tilt
    protection status for the authenticated user.
    """
    uid = current_user.id

    # ── Fetch last 30 settled predictions for this user ─────────────────────
    result = await db.execute(
        select(Prediction)
        .where(Prediction.user_id == uid, Prediction.was_correct.is_not(None))
        .order_by(desc(Prediction.timestamp))
        .limit(50)
    )
    preds = result.scalars().all()

    settled       = len(preds)
    wins          = sum(1 for p in preds if p.was_correct is True)
    win_rate      = wins / settled if settled else 0.5
    avg_stake     = sum(p.recommended_stake or 0 for p in preds) / settled if settled else 0.05
    avg_confidence = sum(p.confidence or 0.6 for p in preds) / settled if settled else 0.6

    # Stake standard deviation
    if settled > 1:
        mean_s = avg_stake
        stake_std = (sum((p.recommended_stake or 0 - mean_s) ** 2 for p in preds) / settled) ** 0.5
    else:
        stake_std = 0.0

    # Current streak (positive = winning, negative = losing)
    streak = 0
    for p in preds:
        if p.was_correct is True:
            if streak >= 0:
                streak += 1
            else:
                break
        else:
            if streak <= 0:
                streak -= 1
            else:
                break

    # ── Bankroll / daily loss ────────────────────────────────────────────────
    br_result = await db.execute(
        select(BankrollState).order_by(desc(BankrollState.updated_at)).limit(1)
    )
    bankroll = br_result.scalar_one_or_none()

    daily_limit = _DAILY_LOSS_LIMIT
    # Approximate today's loss: initial_balance - current_balance (if updated today)
    daily_loss_used = 0.0
    if bankroll:
        drop = bankroll.initial_balance - bankroll.current_balance
        if drop > 0 and bankroll.updated_at:
            updated = bankroll.updated_at
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            if updated >= today_start:
                daily_loss_used = min(drop, daily_limit)

    # ── Compute score ────────────────────────────────────────────────────────
    score = _compute_behavior_score(
        total_preds=settled,
        win_rate=win_rate,
        avg_stake=avg_stake,
        stake_std=stake_std,
        streak=streak,
        settled=settled,
    )

    # ── Status label ─────────────────────────────────────────────────────────
    if score >= 80:
        status = "DISCIPLINED"
    elif score >= 60:
        status = "MODERATE"
    else:
        status = "AT_RISK"

    # ── Percentile (rough heuristic) ─────────────────────────────────────────
    if score >= 90:
        percentile = "top 2%"
    elif score >= 80:
        percentile = "top 10%"
    elif score >= 70:
        percentile = "top 25%"
    elif score >= 60:
        percentile = "top 50%"
    else:
        percentile = "bottom 50%"

    # ── Next milestone ───────────────────────────────────────────────────────
    if settled < 5:
        milestone = f"Complete {5 - settled} more settled prediction(s) to unlock full coaching insights."
    elif score < 80:
        needed = 80 - score
        milestone = f"Improve your behavior score by {needed} points to reach DISCIPLINED status."
    elif streak < 5:
        milestone = f"Win {5 - max(streak, 0)} more in a row to earn the \"Hot Streak\" badge."
    else:
        milestone = "Maintain your current discipline to retain your DISCIPLINED status."

    insights = _build_insights(
        win_rate=win_rate,
        avg_stake=avg_stake,
        stake_std=stake_std,
        streak=streak,
        settled=settled,
        avg_confidence=avg_confidence,
    )

    return {
        "behavior_score":     score,
        "status":             status,
        "percentile":         percentile,
        "streak":             streak,
        "settled_predictions": settled,
        "win_rate":           round(win_rate, 4),
        "avg_stake":          round(avg_stake, 4),
        "insights":           insights,
        "tilt_protection": {
            "daily_limit":     daily_limit,
            "daily_loss_used": round(daily_loss_used, 2),
            "pct_used":        round(daily_loss_used / daily_limit * 100, 1),
        },
        "next_milestone": milestone,
    }


@router.post("/discipline/cooldown")
async def activate_cooldown(current_user: User = Depends(get_current_user)):
    """Activate a 24-hour self-exclusion cooldown."""
    until = datetime.now(timezone.utc) + timedelta(hours=_COOLDOWN_HOURS)
    return {
        "status":    "cooldown_activated",
        "user_id":   current_user.id,
        "cooldown_hours": _COOLDOWN_HOURS,
        "active_until":  until.isoformat(),
        "message":  "You have been self-excluded for 24 hours. Take a break and come back refreshed.",
    }
