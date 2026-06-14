"""app/agents/prediction_agent.py — Autonomous agent for generating match predictions."""

from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from app.agents.base import BaseAgent
from app.db.database import AsyncSessionLocal
from app.db.models import Match, Prediction
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

class PredictionAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="prediction-agent",
            interval_seconds=15 * 60,   # Every 15 minutes
            initial_delay_seconds=30,
        )

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Scan for upcoming matches that lack predictions and generate them using the Orchestrator.
        """
        from app.core.dependencies import get_orchestrator
        from app.services.multi_sport_orchestrator import MultiSportOrchestrator
        from app.services.predict_features import build_predict_features

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now + timedelta(days=3)

        generated_count = 0
        error_count = 0
        matches_checked = 0

        async with AsyncSessionLocal() as db:
            # Find matches in the next 3 days that don't have a prediction yet
            stmt = (
                select(Match)
                .outerjoin(Prediction, Prediction.match_id == Match.id)
                .where(
                    Match.kickoff_time >= now,
                    Match.kickoff_time <= cutoff,
                    Match.status.in_(["scheduled", "upcoming", "open"]),
                    Prediction.id.is_(None)
                )
                .limit(10) # Process in small batches
            )

            result = await db.execute(stmt)
            matches_to_predict = result.scalars().all()
            matches_checked = len(matches_to_predict)

            if not matches_to_predict:
                return {
                    "matches_checked": 0,
                    "predictions_generated": 0,
                    "status": "idle"
                }

            # Initialize orchestrators
            base_orch = get_orchestrator()
            multi_orch = MultiSportOrchestrator(football_orchestrator=base_orch)

            for match in matches_to_predict:
                try:
                    # 1. Build features
                    features = await build_predict_features(db, match.id)

                    # 2. Get prediction (awaiting because MultiSportOrchestrator.predict is now async)
                    pred_data = await multi_orch.predict(features, sport=match.sport or "football")
                    res = pred_data.get("predictions", {})

                    # 3. Create Prediction object
                    prediction = Prediction(
                        match_id=match.id,
                        user_id=None,
                        home_prob=res.get("home_prob", 0.33),
                        draw_prob=res.get("draw_prob", 0.33),
                        away_prob=res.get("away_prob", 0.34),
                        over_25_prob=res.get("over_25_prob", 0.5),
                        btts_prob=res.get("btts_prob", 0.5),
                        confidence=res.get("confidence", {}).get("1x2", 0.5) if isinstance(res.get("confidence"), dict) else 0.5,
                        bet_side=max([("home", res.get("home_prob", 0)), ("draw", res.get("draw_prob", 0)), ("away", res.get("away_prob", 0))], key=lambda x: x[1])[0],
                        entry_odds=features.get("market_odds", {}).get("home", 2.0),
                        data_source=res.get("data_source", "prediction-agent"),
                        timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
                    )

                    db.add(prediction)
                    generated_count += 1
                    logger.info(f"[prediction-agent] Generated prediction for {match.home_team} vs {match.away_team} via {prediction.data_source}")

                    await asyncio.sleep(1)

                except Exception as e:
                    error_count += 1
                    logger.error(f"[prediction-agent] Failed to predict match {match.id}: {e}")

            await db.commit()

        return {
            "matches_checked": matches_checked,
            "predictions_generated": generated_count,
            "errors": error_count,
            "status": "ok"
        }
