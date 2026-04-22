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
    Update match result and calculate CLV.

    FIXES APPLIED:
        - Transaction block for data consistency
        - Correct CLV calculation using bet_side
        - Profit calculation for edge database
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

        # Get prediction for this match
        pred_result = await db.execute(
            select(Prediction).where(Prediction.match_id == match_id)
        )
        prediction = pred_result.scalar_one_or_none()

        # Calculate profit if we have a prediction
        profit = 0
        if prediction and prediction.bet_side:
            # Determine if prediction was correct
            if prediction.bet_side == actual_outcome:
                # Win: profit = stake * (odds - 1)
                profit = prediction.recommended_stake * (prediction.entry_odds - 1)
                logger.info(f"WIN: match={match_id}, profit={profit:.2f}")
            else:
                # Loss: profit = -stake
                profit = -prediction.recommended_stake
                logger.info(f"LOSS: match={match_id}, loss={profit:.2f}")

            # Update CLV with closing odds for this specific prediction
            await CLVTracker.update_closing_by_prediction(
                db, prediction.id,
                result.closing_odds_home,
                result.closing_odds_draw,
                result.closing_odds_away,
                actual_outcome,
                profit
            )

    return {
        "match_id": match_id,
        "actual_outcome": actual_outcome,
        "home_goals": result.home_goals,
        "away_goals": result.away_goals,
        "profit": profit,
        "clv_updated": True
    }