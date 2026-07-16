from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from app.db.database import get_db
from app.db.models import Prediction, Match, User
from app.api.deps import get_current_user
from datetime import datetime, timezone
from typing import Dict, Any

router = APIRouter(prefix="/user/year-review", tags=["Wrapped"])

@router.get("")
async def get_year_review(
    year: int = Query(default=2025),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Aggregate user's performance for a specific year."""
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    base_q = select(Prediction, Match).join(Match, Match.id == Prediction.match_id).where(
        Prediction.user_id == current_user.id,
        Prediction.timestamp.between(start_date, end_date)
    )
    res = await db.execute(base_q)
    rows = res.all()
    total_predictions = len(rows)
    if total_predictions == 0:
        return {"year": year, "total_predictions": 0, "win_rate": 0.0, "best_streak": 0, "top_sport": None, "total_vitcoin_earned": 0.0, "top_market": None, "biggest_win": None, "months": []}
    wins = 0
    total_settled = 0
    total_vitcoin = 0.0
    sport_counts = {}
    market_counts = {}
    biggest_win = None
    months_data = {m: {"predictions": 0, "wins": 0} for m in range(1, 13)}
    current_streak = 0
    best_streak = 0
    rows.sort(key=lambda x: x.Prediction.timestamp)
    for p, m in rows:
        month = p.timestamp.month
        months_data[month]["predictions"] += 1
        sport = m.sport or "football"
        sport_counts[sport] = sport_counts.get(sport, 0) + 1
        market = p.bet_side or "1X2"
        market_counts[market] = market_counts.get(market, 0) + 1
        if p.was_correct is not None:
            total_settled += 1
            if p.was_correct:
                wins += 1
                months_data[month]["wins"] += 1
                current_streak += 1
                best_streak = max(best_streak, current_streak)
                profit = p.settled_profit or 0.0
                total_vitcoin += profit
                if biggest_win is None or profit > biggest_win["profit"]:
                    biggest_win = {"match": f"{m.home_team} vs {m.away_team}", "odds": p.entry_odds, "profit": float(profit)}
            else:
                current_streak = 0
    win_rate = (wins / total_settled) if total_settled > 0 else 0.0
    top_sport = max(sport_counts, key=sport_counts.get) if sport_counts else None
    top_market = max(market_counts, key=market_counts.get) if market_counts else None
    months_list = []
    for m_idx in range(1, 13):
        m_data = months_data[m_idx]
        m_win_rate = (m_data["wins"] / m_data["predictions"]) if m_data["predictions"] > 0 else 0.0
        months_list.append({"month": m_idx, "predictions": m_data["predictions"], "win_rate": round(m_win_rate, 4)})
    return {"year": year, "total_predictions": total_predictions, "win_rate": round(win_rate, 4), "best_streak": best_streak, "top_sport": top_sport, "total_vitcoin_earned": round(total_vitcoin, 2), "top_market": top_market, "biggest_win": biggest_win, "months": months_list}
