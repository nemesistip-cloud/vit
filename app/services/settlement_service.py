import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match, Prediction
from app.modules.merit.service import record_merit_event
from app.modules.merit.models import MeritEventType
from app.services.sportsdb_api import fetch_historical_range
from app.services.clv_tracker import CLVTracker
from app.services.rl_reward import process_settlement_rewards

logger = logging.getLogger(__name__)

class SettlementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def settle_pending_predictions(self) -> Dict:
        """
        Scan for matches that have ended but are not yet settled,
        fetch results, and update prediction status + merit scores.
        """
        # 1. Find matches that are scheduled/live but should have finished
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = select(Match).where(
            and_(
                Match.kickoff_time <= now - timedelta(hours=4),
                Match.actual_outcome.is_(None)
            )
        )
        res = await self.db.execute(stmt)
        pending_matches = res.scalars().all()

        if not pending_matches:
            return {"settled_matches": 0, "predictions_updated": 0}

        # 2. Fetch recent results from API
        recent_results = await fetch_historical_range(days_back=2)
        result_map = {r['external_id']: r for r in recent_results if r.get('external_id')}

        settled_count = 0
        pred_count = 0

        for match in pending_matches:
            api_result = result_map.get(match.external_id)
            if not api_result:
                continue

            # 3. Update Match
            match.home_goals = api_result.get("home_goals")
            match.away_goals = api_result.get("away_goals")
            match.actual_outcome = api_result.get("actual_outcome")
            match.status = "completed"

            actual_outcome = match.actual_outcome

            # 4. Settle predictions
            pred_stmt = select(Prediction).where(Prediction.match_id == match.id)
            p_res = await self.db.execute(pred_stmt)
            predictions = p_res.scalars().all()

            for pred in predictions:
                if not pred.bet_side:
                    continue

                won = pred.bet_side == actual_outcome
                stake = float(pred.recommended_stake or 0.0)
                odds = float(pred.entry_odds or 2.0)
                profit = stake * (odds - 1) if won else -stake

                pred.was_correct = won
                pred.settled_profit = profit

                # Record Merit
                if pred.user_id:
                    event_type = MeritEventType.PREDICTION_CORRECT if won else MeritEventType.PREDICTION_INCORRECT
                    await record_merit_event(
                        self.db, pred.user_id,
                        event_type,
                        ref_id=f"pred_{pred.id}",
                        description=f"Prediction on {match.home_team} vs {match.away_team} settled"
                    )

                # Update CLV
                await CLVTracker.update_closing_by_prediction(
                    self.db, pred.id,
                    None, None, None, # We don't always have closing odds from free API
                    actual_outcome,
                    profit
                )
                pred_count += 1

            # RL rewards
            try:
                await process_settlement_rewards(self.db, match.id, match.home_goals, match.away_goals)
            except Exception:
                pass

            settled_count += 1

        await self.db.commit()
        return {
            "settled_matches": settled_count,
            "predictions_updated": pred_count
        }

async def run_auto_settlement(db: AsyncSession):
    svc = SettlementService(db)
    return await svc.settle_pending_predictions()
