"""Leaderboard endpoint — prediction accuracy, ROI, streak, and XP rankings.

v4.5: Replaced N+1 query pattern with a single SQL aggregation.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Prediction

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])


@router.get("")
async def get_leaderboard(
    category: str = Query("win_rate", enum=["win_rate", "xp", "streak", "predictions"]),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Public leaderboard — no auth required. Uses a single aggregated SQL query."""

    settled_pred = case((Prediction.final_ev.is_not(None), 1), else_=0)
    win_pred     = case(
        (
            (Prediction.final_ev.is_not(None)) & (Prediction.final_ev > 0),
            1,
        ),
        else_=0,
    )
    roi_pred = func.coalesce(Prediction.final_ev, 0.0)

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
        .where(User.is_active == True, User.is_banned == False)
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
        roi           = round(float(row.total_roi or 0.0), 2)

        board.append({
            "user_id":           row.id,
            "username":          row.username,
            "total_predictions": int(row.total_predictions or 0),
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

    return {"category": category, "entries": board[:limit], "total_users": len(board)}
