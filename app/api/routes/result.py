# app/api/routes/result.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Match, Prediction
from app.schemas.schemas import ResultUpdate
from app.services.clv_tracker import CLVTracker
from app.services.edge_database import EdgeDatabase
from app.services.market_utils import MarketUtils
from app.api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["results"], dependencies=[Depends(verify_api_key)])


@router.post("/{match_id}")
async def update_result(
    match_id: int,
    result: ResultUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update match result and calculate CLV for ALL predictions on this match.

    FIXES APPLIED:
        - Handles multiple predictions per match (multi-user support)
        - Sets was_correct + settled_profit on each Prediction row
        - Transaction block for data consistency
        - Correct CLV calculation using bet_side
    """

    async with db.begin():
        # Get match
        match_result = await db.execute(select(Match).where(Match.id == match_id))
        match = match_result.scalar_one_or_none()

        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        # Update match with actual results
        match.home_goals = result.home_goals
        match.away_goals = result.away_goals
        match.closing_odds_home = result.closing_odds_home
        match.closing_odds_draw = result.closing_odds_draw
        match.closing_odds_away = result.closing_odds_away
        match.status = "completed"

        # Determine actual outcome
        if result.home_goals > result.away_goals:
            actual_outcome = "home"
        elif result.home_goals == result.away_goals:
            actual_outcome = "draw"
        else:
            actual_outcome = "away"

        match.actual_outcome = actual_outcome

        # Get ALL predictions for this match (multi-user support)
        pred_result = await db.execute(
            select(Prediction).where(Prediction.match_id == match_id)
        )
        predictions = pred_result.scalars().all()

        total_profit = 0.0
        settled_count = 0

        for prediction in predictions:
            if not prediction.bet_side:
                continue

            won = prediction.bet_side == actual_outcome
            stake = float(prediction.recommended_stake or 0.0)
            odds = float(prediction.entry_odds or 2.0)
            profit = stake * (odds - 1) if won else -stake

            # Stamp correctness directly on the prediction row
            prediction.was_correct = won
            prediction.settled_profit = profit

            if won:
                logger.info(f"WIN: match={match_id}, prediction={prediction.id}, profit={profit:.2f}")
            else:
                logger.info(f"LOSS: match={match_id}, prediction={prediction.id}, loss={profit:.2f}")

            # Update CLV with closing odds for this specific prediction
            await CLVTracker.update_closing_by_prediction(
                db, prediction.id,
                result.closing_odds_home,
                result.closing_odds_draw,
                result.closing_odds_away,
                actual_outcome,
                profit
            )

            total_profit += profit
            settled_count += 1

    return {
        "match_id": match_id,
        "actual_outcome": actual_outcome,
        "home_goals": result.home_goals,
        "away_goals": result.away_goals,
        "ft_score": f"{result.home_goals}-{result.away_goals}",
        "predictions_settled": settled_count,
        "total_profit": round(total_profit, 4),
        "clv_updated": True
    }
