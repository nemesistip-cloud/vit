"""Leaderboard endpoint — prediction accuracy, ROI, streak, and XP rankings."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
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
    """Public leaderboard — no auth required."""
    users_res = await db.execute(
        select(User).where(User.is_active == True, User.is_banned == False)
        .limit(200)
    )
    users = users_res.scalars().all()

    board = []
    for user in users:
        preds = await db.execute(
            select(Prediction).where(Prediction.user_id == user.id)
        )
        predictions = preds.scalars().all()
        total = len(predictions)
        settled = [p for p in predictions if p.final_ev is not None]
        wins = sum(1 for p in settled if (p.final_ev or 0) > 0)
        win_rate = (wins / len(settled) * 100) if settled else 0.0
        roi = sum((p.final_ev or 0) for p in settled)

        board.append({
            "user_id": user.id,
            "username": user.username,
            "total_predictions": total,
            "win_rate": round(win_rate, 1),
            "roi": round(roi, 2),
            "xp": getattr(user, "total_xp", 0) or 0,
            "streak": getattr(user, "current_streak", 0) or 0,
            "subscription_tier": getattr(user, "subscription_tier", "viewer") or "viewer",
        })

    if category == "win_rate":
        board.sort(key=lambda x: x["win_rate"], reverse=True)
    elif category == "xp":
        board.sort(key=lambda x: x["xp"], reverse=True)
    elif category == "streak":
        board.sort(key=lambda x: x["streak"], reverse=True)
    elif category == "predictions":
        board.sort(key=lambda x: x["total_predictions"], reverse=True)

    for i, entry in enumerate(board[:limit], 1):
        entry["rank"] = i

    return {"category": category, "entries": board[:limit], "total_users": len(board)}
