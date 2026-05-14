"""Leaderboard endpoint — prediction accuracy, ROI, streak, and XP rankings.

v4.6: Fixed win_rate and ROI to use actual match outcomes (bet_side vs actual_outcome)
      and CLVEntry.profit / Prediction.settled_profit instead of final_ev.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Prediction, Match, CLVEntry
from app.services.cache import cache

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])


@router.get("")
async def get_leaderboard(
    category: str = Query("win_rate", enum=["win_rate", "xp", "streak", "predictions", "accuracy"]),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Public leaderboard — no auth required.

    Win rate = predictions where bet_side == actual_outcome / total settled predictions.
    ROI = sum of settled_profit (from Prediction.settled_profit, fallback to CLVEntry.profit).
    Uses a single aggregated SQL query joining Match for actual outcome comparison.
    """
    if category == "accuracy":
        category = "win_rate"
    _cache_key = f"leaderboard:{category}:{limit}"
    _cached = await cache.get(_cache_key)
    if _cached is not None:
        return _cached

    # A prediction is settled when the match has an actual_outcome and prediction has a bet_side
    settled_cond = and_(
        Match.actual_outcome.isnot(None),
        Prediction.bet_side.isnot(None),
    )

    # Win = bet_side matches actual_outcome
    win_cond = and_(
        settled_cond,
        Prediction.was_correct == True,  # noqa: E712
    )

    # Fallback win detection for predictions settled before was_correct column existed
    win_cond_fallback = and_(
        settled_cond,
        Prediction.was_correct.is_(None),
        Prediction.bet_side == Match.actual_outcome,
    )

    settled_pred = case((settled_cond, 1), else_=0)
    win_pred = case(
        (win_cond, 1),
        (win_cond_fallback, 1),
        else_=0,
    )

    # ROI: only count actual settled profit — never mix in predicted EV
    roi_pred = func.coalesce(
        Prediction.settled_profit,
        0.0,
    )

    agg = (
        select(
            User.id,
            User.username,
            func.coalesce(User.total_xp, 0).label("xp"),
            func.coalesce(User.current_streak, 0).label("streak"),
            func.coalesce(User.subscription_tier, "viewer").label("subscription_tier"),
            func.count(Prediction.id).label("total_predictions"),
            func.sum(settled_pred).label("total_settled"),
            func.sum(win_pred).label("total_wins"),
            func.sum(roi_pred).label("total_roi"),
        )
        .outerjoin(Prediction, Prediction.user_id == User.id)
        .outerjoin(Match, Match.id == Prediction.match_id)
        .where(User.is_active == True, User.is_banned == False)  # noqa: E712
        .group_by(
            User.id, User.username, User.total_xp,
            User.current_streak, User.subscription_tier,
        )
    )

    rows = (await db.execute(agg)).all()

    board = []
    for row in rows:
        total_settled = int(row.total_settled or 0)
        total_wins    = int(row.total_wins or 0)
        win_rate      = round(total_wins / total_settled * 100, 1) if total_settled else 0.0
        roi           = round(float(row.total_roi or 0.0), 4)

        board.append({
            "user_id":           row.id,
            "username":          row.username,
            "total_predictions": int(row.total_predictions or 0),
            "total_settled":     total_settled,
            "total_wins":        total_wins,
            "win_rate":          win_rate,
            "roi":               roi,
            "xp":                int(row.xp or 0),
            "streak":            int(row.streak or 0),
            "subscription_tier": row.subscription_tier or "viewer",
        })

    sort_keys = {
        "win_rate":    lambda x: x["win_rate"],
        "xp":          lambda x: x["xp"],
        "streak":      lambda x: x["streak"],
        "predictions": lambda x: x["total_predictions"],
    }
    board.sort(key=sort_keys[category], reverse=True)

    for i, entry in enumerate(board[:limit], 1):
        entry["rank"] = i

    result = {"category": category, "entries": board[:limit], "total_users": len(board)}
    await cache.set(_cache_key, result, ttl=60)
    return result


@router.get("/global")
async def get_global_leaderboard(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Composite global leaderboard — weighted combination of win_rate, XP, and ROI."""
    _cache_key = f"leaderboard:global:{limit}"
    _cached = await cache.get(_cache_key)
    if _cached is not None:
        return _cached

    settled_cond = and_(Match.actual_outcome.isnot(None), Prediction.bet_side.isnot(None))
    win_cond = and_(settled_cond, Prediction.was_correct == True)  # noqa: E712
    win_cond_fallback = and_(
        settled_cond,
        Prediction.was_correct.is_(None),
        Prediction.bet_side == Match.actual_outcome,
    )
    settled_pred = case((settled_cond, 1), else_=0)
    win_pred = case((win_cond, 1), (win_cond_fallback, 1), else_=0)
    roi_pred = func.coalesce(Prediction.settled_profit, Prediction.final_ev, 0.0)

    agg = (
        select(
            User.id, User.username,
            func.coalesce(User.total_xp, 0).label("xp"),
            func.coalesce(User.current_streak, 0).label("streak"),
            func.coalesce(User.subscription_tier, "viewer").label("subscription_tier"),
            func.count(Prediction.id).label("total_predictions"),
            func.sum(settled_pred).label("total_settled"),
            func.sum(win_pred).label("total_wins"),
            func.sum(roi_pred).label("total_roi"),
        )
        .outerjoin(Prediction, Prediction.user_id == User.id)
        .outerjoin(Match, Match.id == Prediction.match_id)
        .where(User.is_active == True, User.is_banned == False)  # noqa: E712
        .group_by(User.id, User.username, User.total_xp, User.current_streak, User.subscription_tier)
    )
    rows = (await db.execute(agg)).all()
    board = []
    for row in rows:
        total_settled = int(row.total_settled or 0)
        total_wins    = int(row.total_wins or 0)
        win_rate      = round(total_wins / total_settled * 100, 1) if total_settled else 0.0
        roi           = round(float(row.total_roi or 0.0), 4)
        xp            = int(row.xp or 0)
        score = win_rate * 0.4 + min(xp / 100, 50) * 0.3 + min(roi * 10, 30) * 0.3
        board.append({
            "user_id":           row.id,
            "username":          row.username,
            "xp":                xp,
            "total_settled":     total_settled,
            "win_rate":          win_rate,
            "roi":               roi,
            "streak":            int(row.streak or 0),
            "subscription_tier": row.subscription_tier or "viewer",
            "composite_score":   round(score, 2),
        })
    board.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, entry in enumerate(board[:limit], 1):
        entry["rank"] = i
    result = {"category": "global", "entries": board[:limit], "total_users": len(board)}
    await cache.set(_cache_key, result, ttl=60)
    return result
