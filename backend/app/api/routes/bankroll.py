"""app/api/routes/bankroll.py
Bankroll Management System — Phase 3c

GET  /api/bankroll/state       → current bankroll state + Kelly recommendation
GET  /api/bankroll/history     → 30d P&L chart data
POST /api/bankroll/set-limit   → set max daily loss limit
POST /api/bankroll/reset       → reset bankroll to initial state (admin)
GET  /api/bankroll/kelly        → Kelly criterion calculator for a given edge/odds
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import BankrollState, Prediction, Match
from app.auth.dependencies import get_current_user
from app.db.models import User

# Ensure all relationship-referenced models are registered before mapper configures
import app.modules.notifications.models  # registers Notification, NotificationPreference  # noqa: F401

router = APIRouter(prefix="/api/bankroll", tags=["Bankroll"])
logger = logging.getLogger(__name__)

_DEFAULT_BALANCE = 10_000.0
_MAX_KELLY_FRACTION = 0.10   # cap at 10% of bankroll
_QUARTER_KELLY = 0.25        # use quarter-Kelly for safety


class SetLimitRequest(BaseModel):
    max_daily_loss: float = Field(..., ge=0, le=100_000, description="Max daily loss in stake units")
    max_stake_pct: Optional[float] = Field(None, ge=0.001, le=0.20, description="Max stake as fraction of bankroll")


class KellyRequest(BaseModel):
    win_probability: float = Field(..., ge=0.01, le=0.99)
    decimal_odds: float = Field(..., ge=1.01, le=50.0)
    bankroll: Optional[float] = Field(None, ge=1.0)


def _kelly_fraction(win_prob: float, decimal_odds: float) -> float:
    b = decimal_odds - 1.0
    q = 1.0 - win_prob
    k = (b * win_prob - q) / b
    return max(0.0, min(_MAX_KELLY_FRACTION, k))


def _quarter_kelly(win_prob: float, decimal_odds: float) -> float:
    return round(_kelly_fraction(win_prob, decimal_odds) * _QUARTER_KELLY, 6)


async def _get_or_create_state(db: AsyncSession) -> BankrollState:
    res = await db.execute(select(BankrollState).order_by(desc(BankrollState.id)).limit(1))
    state = res.scalar_one_or_none()
    if not state:
        state = BankrollState(
            initial_balance=_DEFAULT_BALANCE,
            current_balance=_DEFAULT_BALANCE,
            peak_balance=_DEFAULT_BALANCE,
            total_staked=0.0,
            total_profit=0.0,
            total_bets=0,
            winning_bets=0,
            losing_bets=0,
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)
    return state


async def _compute_stats(db: AsyncSession) -> Dict[str, Any]:
    """Compute live P&L stats from the predictions table."""
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)

    res = await db.execute(
        select(
            func.count(Prediction.id).label("total"),
            func.sum(case((Prediction.was_correct == True, 1.0), else_=0.0)).label("wins"),  # noqa: E712
            func.coalesce(func.sum(Prediction.settled_profit), 0.0).label("profit"),
            func.coalesce(func.sum(Prediction.entry_odds * Prediction.recommended_stake), 0.0).label("total_staked"),
        ).join(Match, Match.id == Prediction.match_id).where(
            and_(
                Match.actual_outcome.isnot(None),
                Prediction.was_correct.isnot(None),
            )
        )
    )
    agg = res.one()

    res_30d = await db.execute(
        select(
            func.count(Prediction.id).label("total"),
            func.sum(case((Prediction.was_correct == True, 1.0), else_=0.0)).label("wins"),  # noqa: E712
            func.coalesce(func.sum(Prediction.settled_profit), 0.0).label("profit"),
        ).join(Match, Match.id == Prediction.match_id).where(
            and_(
                Match.actual_outcome.isnot(None),
                Prediction.was_correct.isnot(None),
                Prediction.timestamp >= cutoff_30d,
            )
        )
    )
    agg_30d = res_30d.one()

    total = int(agg.total or 0)
    wins = int(agg.wins or 0)
    profit = float(agg.profit or 0.0)
    staked = float(agg.total_staked or 0.0)
    win_rate = round(wins / total * 100, 1) if total else 0.0
    roi = round(profit / staked * 100, 2) if staked else 0.0

    t30 = int(agg_30d.total or 0)
    w30 = int(agg_30d.wins or 0)
    p30 = float(agg_30d.profit or 0.0)
    wr30 = round(w30 / t30 * 100, 1) if t30 else 0.0

    return {
        "all_time": {"total": total, "wins": wins, "losses": total - wins, "win_rate": win_rate, "profit": round(profit, 4), "roi_pct": roi},
        "last_30d": {"total": t30, "wins": w30, "losses": t30 - w30, "win_rate": wr30, "profit": round(p30, 4)},
        "win_rate_decimal": win_rate / 100 if win_rate else 0.5,
    }


async def _daily_pnl_history(db: AsyncSession, days: int = 30) -> List[Dict]:
    """Build daily P&L series for charting."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    res = await db.execute(
        select(
            func.date(Prediction.timestamp).label("day"),
            func.count(Prediction.id).label("count"),
            func.sum(case((Prediction.was_correct == True, 1.0), else_=0.0)).label("wins"),  # noqa: E712
            func.coalesce(func.sum(Prediction.settled_profit), 0.0).label("profit"),
        ).join(Match, Match.id == Prediction.match_id).where(
            and_(
                Match.actual_outcome.isnot(None),
                Prediction.was_correct.isnot(None),
                Prediction.timestamp >= cutoff,
            )
        ).group_by(func.date(Prediction.timestamp)).order_by(func.date(Prediction.timestamp))
    )

    rows = res.all()
    history = []
    running_pnl = 0.0
    for row in rows:
        day_profit = float(row.profit or 0.0)
        running_pnl += day_profit
        history.append({
            "date":        str(row.day),
            "count":       int(row.count or 0),
            "wins":        int(row.wins or 0),
            "profit":      round(day_profit, 4),
            "cumulative":  round(running_pnl, 4),
        })
    return history


@router.get("/state")
async def get_bankroll_state(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    state = await _get_or_create_state(db)
    stats = await _compute_stats(db)

    win_rate = stats["win_rate_decimal"]
    avg_odds = 2.0  # conservative estimate when we don't have exact odds

    full_kelly = _kelly_fraction(win_rate, avg_odds)
    quarter_k = _quarter_kelly(win_rate, avg_odds)
    suggested_stake = round(state.current_balance * quarter_k, 2)

    drawdown = 0.0
    if state.peak_balance > 0:
        drawdown = round((state.peak_balance - state.current_balance) / state.peak_balance * 100, 2)

    return {
        "balance": {
            "initial":  state.initial_balance,
            "current":  state.current_balance,
            "peak":     state.peak_balance,
            "drawdown_pct": drawdown,
        },
        "stats": stats,
        "kelly": {
            "full_kelly_pct":    round(full_kelly * 100, 2),
            "quarter_kelly_pct": round(quarter_k * 100, 2),
            "suggested_stake":   suggested_stake,
            "basis_win_rate":    round(win_rate * 100, 1),
            "basis_avg_odds":    avg_odds,
        },
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
    }


@router.get("/history")
async def get_bankroll_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = await _daily_pnl_history(db, days=min(days, 365))
    return {"days": days, "history": history, "count": len(history)}


@router.post("/set-limit")
async def set_bankroll_limit(
    body: SetLimitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    state = await _get_or_create_state(db)
    # Store limits as extra metadata — extend BankrollState later if needed
    # For now, return acknowledgement with Kelly-adjusted suggestion
    return {
        "status":            "ok",
        "max_daily_loss":    body.max_daily_loss,
        "max_stake_pct":     body.max_stake_pct,
        "current_balance":   state.current_balance,
        "max_daily_loss_pct": round(body.max_daily_loss / state.current_balance * 100, 2) if state.current_balance else 0,
    }


@router.post("/kelly")
async def calculate_kelly(
    body: KellyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculate Kelly criterion stake for given win probability + odds."""
    full_k = _kelly_fraction(body.win_probability, body.decimal_odds)
    quarter_k = full_k * _QUARTER_KELLY

    bankroll = body.bankroll
    if not bankroll:
        state = await _get_or_create_state(db)
        bankroll = state.current_balance

    edge = round((body.win_probability * body.decimal_odds - 1) * 100, 2)

    return {
        "win_probability":   body.win_probability,
        "decimal_odds":      body.decimal_odds,
        "edge_pct":          edge,
        "full_kelly_pct":    round(full_k * 100, 2),
        "quarter_kelly_pct": round(quarter_k * 100, 2),
        "recommended_stake": round(bankroll * quarter_k, 2),
        "bankroll":          bankroll,
        "positive_ev":       edge > 0,
    }
