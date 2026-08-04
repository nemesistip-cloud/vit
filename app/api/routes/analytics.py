"""Analytics endpoint — system-wide metrics, model performance, and user stats."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Match, Prediction, CLVEntry
from app.core.cache import cache
from app.config import APP_VERSION as VERSION

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def _date_filter(query, model, date_from: str | None, date_to: str | None):
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.where(model.created_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(model.created_at <= dt)
        except ValueError:
            pass
    return query


# ── 1. Platform Summary ───────────────────────────────────────────────

@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """Single endpoint returning all key metrics for the analytics dashboard."""
    _cached = await cache.get("analytics:summary")
    if _cached is not None:
        return _cached

    total_q  = await db.execute(select(func.count()).select_from(Prediction))
    total    = total_q.scalar() or 0

    settled_q = await db.execute(
        select(func.count()).select_from(Prediction)
        .join(Match, Match.id == Prediction.match_id)
        .where(Match.actual_outcome.isnot(None))
    )
    settled  = settled_q.scalar() or 0

    clv_q = await db.execute(
        select(func.avg(CLVEntry.clv)).select_from(CLVEntry)
        .where(CLVEntry.clv.isnot(None))
    )
    avg_clv = round(float(clv_q.scalar() or 0), 4)

    edge_q = await db.execute(
        select(func.avg(Prediction.vig_free_edge)).select_from(Prediction)
        .where(Prediction.vig_free_edge.isnot(None))
        .where(Prediction.vig_free_edge > 0)
    )
    avg_edge = round(float(edge_q.scalar() or 0), 4)

    # Aggregate User Metrics
    user_stats_q = await db.execute(
        select(
            func.count(User.id),
            func.sum(func.coalesce(User.merit_score, 0)),
            func.sum(func.coalesce(User.total_xp, 0))
        ).where(User.is_active == True)
    )
    user_stats = user_stats_q.one()
    total_users = user_stats[0] or 0
    total_merit = float(user_stats[1] or 0)
    total_xp = float(user_stats[2] or 0)

    # Niche market count
    niche_q = await db.execute(
        select(func.count(Match.id)).where(Match.market_type == "niche")
    )
    active_niche = niche_q.scalar() or 0

    bankroll_data = {}
    try:
        from app.services.bankroll import BankrollManager
        bm = BankrollManager(db)
        await bm.load_state()
        bankroll_data = bm.bankroll.to_dict()
    except Exception as exc:
        logger.debug(f"[analytics/summary] bankroll unavailable: {exc}")

    result = {
        "total_predictions": total,
        "total":             total,
        "settled":           settled,
        "pending":           total - settled,
        "avg_clv":           avg_clv,
        "avg_edge":          avg_edge,
        "total_users":       total_users,
        "total_merit":       total_merit,
        "total_xp":          total_xp,
        "active_niche":      active_niche,
        "bankroll":          bankroll_data,
        "version":           VERSION,
    }
    await cache.set("analytics:summary", result, ttl=30)
    return result


# ── 2. Model Breakdown ────────────────────────────────────────────────

@router.get("/model-contribution")
async def get_model_contribution(
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Breakdown of how much each of the 13 models contributed to predictions.
    Shows participation rate, avg confidence, and accuracy where available.
    """
    q = (
        select(Match, Prediction)
        .join(Prediction, Match.id == Prediction.match_id)
    )
    q = _date_filter(q, Prediction, date_from, date_to)

    result = await db.execute(q.limit(500))
    rows   = result.all()

    contribution: dict = {}
    data_source = "model_insights"

    for r in rows:
        insights = r.Prediction.model_insights or []
        actual   = r.Match.actual_outcome
        bet_side = r.Prediction.bet_side

        for m in insights:
            name = m.get("model_name") or m.get("model_type") or "unknown"
            if name not in contribution:
                contribution[name] = {
                    "model_name":   name,
                    "model_type":   m.get("model_type", ""),
                    "appearances":  0,
                    "failures":     0,
                    "total_weight": 0.0,
                    "conf_sum":     0.0,
                    "correct":      0,
                    "settled":      0,
                }
            c = contribution[name]
            c["appearances"] += 1
            c["total_weight"] += float(m.get("weight", 0))
            c["conf_sum"]     += float(m.get("confidence", 0))

            if actual:
                c["settled"] += 1
                if m.get("prediction") == actual:
                    c["correct"] += 1
                elif bet_side == actual: # if the ensemble picked correctly but this sub-model didn't, or vice-versa
                    pass

    # Finalize stats
    final = []
    for name, stats in contribution.items():
        stats["avg_confidence"] = round(stats["conf_sum"] / stats["appearances"], 4) if stats["appearances"] > 0 else 0
        stats["accuracy"]       = round(stats["correct"] / stats["settled"], 4) if stats["settled"] > 0 else None
        final.append(stats)

    return {
        "models": sorted(final, key=lambda x: x["appearances"], reverse=True),
        "total_samples": len(rows),
        "source": data_source
    }


# ── 3. System Metrics ─────────────────────────────────────────────────

@router.get("/system")
async def get_system_analytics(db: AsyncSession = Depends(get_db)):
    """System-level analytics: user counts, model status, platform health."""
    summary = await get_summary(db)

    total_users = summary["total_users"]
    active_users = total_users # Assuming active for now if not tracked separately

    validator_count_q = await db.execute(
        select(func.count(User.id)).where(User.role == "validator")
    )
    validator_count = validator_count_q.scalar() or 0

    total_matches_q = await db.execute(select(func.count(Match.id)))
    total_matches = total_matches_q.scalar() or 0

    settled_matches_q = await db.execute(
        select(func.count(Match.id)).where(Match.actual_outcome.isnot(None))
    )
    settled_matches = settled_matches_q.scalar() or 0

    model_count = 0
    try:
        from app.core.dependencies import get_orchestrator
        orch = get_orchestrator()
        if orch:
            model_count = orch.num_models_ready()
    except Exception as exc:
        logger.debug(f"[analytics/system] orchestrator unavailable: {exc}")

    vit_price = 0.001
    try:
        from app.modules.wallet.pricing import VITCoinPricingEngine
        engine = VITCoinPricingEngine(db)
        prices = await engine.get_current_price()
        from decimal import Decimal as _D
        vit_price = float(prices.get("usd", _D("0.001")))
    except Exception as exc:
        logger.debug(f"[analytics/system] VIT price unavailable: {exc}")

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "validators": validator_count,
        },
        "matches": {
            "total": total_matches,
            "settled": settled_matches,
            "pending": total_matches - settled_matches,
        },
        "predictions": {
            "total": summary["total_predictions"],
            "avg_confidence": summary["avg_clv"], # Fallback if not tracked
            "avg_edge": summary["avg_edge"],
        },
        "models": {
            "active_count": model_count,
        },
        "vitcoin": {
            "price_usd": vit_price,
        },
        "version": VERSION,
    }


# ── 9. Leaderboard — Validators ───────────────────────────────────────
_VAL_SORT_ALIASES = {
    "trust": "trust_score",
    "trust_score": "trust_score",
    "acc": "accuracy_rate",
    "accuracy": "accuracy_rate",
    "accuracy_rate": "accuracy_rate",
    "stake": "stake_amount",
    "stake_amount": "stake_amount",
}


@router.get("/leaderboard/validators")
async def get_validator_leaderboard(
    sort_by: str = Query("trust_score"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return validators ranked by trust score, accuracy, or stake."""
    sort_col = _VAL_SORT_ALIASES.get(sort_by, "trust_score")
    try:
        from app.modules.blockchain.models import ValidatorProfile
        from app.db.models import User as _User

        col = getattr(ValidatorProfile, sort_col, ValidatorProfile.trust_score)
        result = await db.execute(
            select(ValidatorProfile, _User)
            .join(_User, ValidatorProfile.user_id == _User.id)
            .where(ValidatorProfile.status == "active")
            .order_by(col.desc())
            .limit(limit)
        )
        rows = result.all()

        leaderboard = []
        for i, (vp, user) in enumerate(rows):
            acc = (
                float(vp.accurate_predictions) / float(vp.total_predictions)
                if vp.total_predictions else 0.0
            )
            leaderboard.append({
                "rank": i + 1,
                "username": user.username,
                "trust_score": float(vp.trust_score or 0),
                "accuracy_rate": acc,
                "stake_amount": float(vp.stake_amount or 0),
                "total_predictions": vp.total_predictions or 0,
                "status": vp.status,
                "joined_at": vp.joined_at.isoformat() if vp.joined_at else None,
            })

        return {"leaderboard": leaderboard, "total": len(leaderboard), "sort_by": sort_by}
    except Exception as e:
        logger.error(f"validator leaderboard error: {e}", exc_info=True)
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=503, detail=f"Leaderboard temporarily unavailable: {e}")


# ── 10. Leaderboard — Users ───────────────────────────────────────────
_USER_SORT_ALIASES = {
    "xp": "xp",
    "roi": "roi",
    "profit": "profit",
    "win_rate": "win_rate",
    "w/r": "win_rate",
    "wr": "win_rate",
    "predictions": "predictions",
    "stake": "total_staked",
    "stake_amount": "total_staked",
    "total_staked": "total_staked",
}


@router.get("/leaderboard/users")
async def get_user_leaderboard(
    sort_by: str = Query("xp"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return top users ranked by XP, ROI, profit, win rate, predictions, or stake."""
    sort_key = _USER_SORT_ALIASES.get((sort_by or "").lower(), "xp")
    try:
        result = await db.execute(
            select(User).where(User.is_active == True, User.is_banned == False)
        )
        users = result.scalars().all()

        # Default unit stake (VITCoin) used when CLVEntry has no recorded stake.
        UNIT_STAKE = 1.0

        leaderboard = []
        for u in users:
            u_pred_sub = select(Prediction.id).where(Prediction.user_id == u.id).subquery()

            total_preds = (await db.execute(
                select(func.count(Prediction.id)).where(Prediction.user_id == u.id)
            )).scalar() or 0

            settled = (await db.execute(
                select(func.count(CLVEntry.id))
                .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
                .where(CLVEntry.bet_outcome.in_(["win", "loss"]))
            )).scalar() or 0

            wins = (await db.execute(
                select(func.count(CLVEntry.id))
                .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
                .where(CLVEntry.bet_outcome == "win")
            )).scalar() or 0

            # Real P&L from CLV ledger when present, else simulated from outcomes
            profit_sum = (await db.execute(
                select(func.coalesce(func.sum(CLVEntry.profit), 0.0))
                .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
                .where(CLVEntry.bet_outcome.in_(["win", "loss"]))
            )).scalar() or 0.0

            if settled > 0 and (profit_sum is None or float(profit_sum) == 0.0):
                # Fall back: estimate using avg odds * UNIT_STAKE
                avg_odds = (await db.execute(
                    select(func.coalesce(func.avg(CLVEntry.entry_odds), 0.0))
                    .where(CLVEntry.prediction_id.in_(select(u_pred_sub.c.id)))
                    .where(CLVEntry.bet_outcome.in_(["win", "loss"]))
                )).scalar() or 0.0
                profit_sum = (wins * (float(avg_odds) - 1.0) - (settled - wins)) * UNIT_STAKE

            total_staked = float(settled) * UNIT_STAKE
            roi = (float(profit_sum) / total_staked) if total_staked > 0 else 0.0

            stored_xp = getattr(u, "total_xp", None) or 0
            xp = stored_xp if stored_xp > 0 else (total_preds * 10 + wins * 20)
            win_rate = round(wins / settled, 4) if settled > 0 else 0.0
            streak = getattr(u, "current_streak", 0) or 0

            tier = u.subscription_tier or "viewer"
            level_map = {"viewer": "Novice", "analyst": "Analyst", "pro": "Pro", "elite": "Elite"}

            leaderboard.append({
                "username": u.username,
                "xp": xp,
                "win_rate": win_rate,
                "predictions": total_preds,
                "total_bets": settled,
                "settled": settled,
                "wins": wins,
                "total_staked": round(total_staked, 4),
                "profit": round(float(profit_sum), 4),
                "roi": round(float(roi), 4),
                "streak": streak,
                "level": level_map.get(tier, "Novice"),
                "tier": tier,
            })

        leaderboard.sort(key=lambda x: x.get(sort_key, 0) or 0, reverse=True)
        leaderboard = leaderboard[:limit]
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        return {"leaderboard": leaderboard, "total": len(leaderboard), "sort_by": sort_key}
    except Exception as e:
        logger.error(f"user leaderboard error: {e}", exc_info=True)
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=503, detail=f"Leaderboard temporarily unavailable: {e}")


# ── Compatibility aliases ──────────────────────────────────────────────────────

@router.get("/overview")
async def get_overview_alias(db: AsyncSession = Depends(get_db)):
    """Alias for /summary — returns all key analytics metrics."""
    return await get_summary(db)


@router.get("/model-performance")
async def get_model_performance_alias(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Alias for /model-contribution — per-model accuracy & weight breakdown."""
    return await get_model_contribution(date_from=date_from, date_to=date_to, db=db)
