"""app/agents/prediction_agent.py — Autonomous agent for generating match predictions."""

from __future__ import annotations

import logging
import asyncio
import math
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
                    features = await build_predict_features(
                        db,
                        match.home_team,
                        match.away_team,
                        match.league,
                    )

                    # 2. Get prediction (awaiting because MultiSportOrchestrator.predict is now async)
                    pred_data = await multi_orch.predict(features, sport=match.sport or "football")
                    res = pred_data.get("predictions", {})

                    probabilities = {
                        key: res.get(key)
                        for key in ("home_prob", "draw_prob", "away_prob")
                    }
                    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in probabilities.values()):
                        raise ValueError("prediction probabilities are unavailable")
                    if any(value < 0 or value > 1 for value in probabilities.values()):
                        raise ValueError("prediction probabilities are outside [0, 1]")
                    if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=0.01):
                        raise ValueError("prediction probabilities do not sum to 1")

                    confidence_value = res.get("confidence", {}).get("1x2") if isinstance(res.get("confidence"), dict) else None
                    if (
                        not isinstance(confidence_value, (int, float))
                        or not math.isfinite(confidence_value)
                        or not 0 <= confidence_value <= 1
                    ):
                        raise ValueError("prediction confidence is unavailable")

                    optional_probabilities = {}
                    for key in ("over_25_prob", "btts_prob"):
                        value = res.get(key)
                        if value is not None and (
                            not isinstance(value, (int, float))
                            or not math.isfinite(value)
                            or not 0 <= value <= 1
                        ):
                            raise ValueError(f"{key} is outside [0, 1]")
                        optional_probabilities[key] = value

                    market_odds = features.get("market_odds", {})
                    entry_odds = market_odds.get("home") if isinstance(market_odds, dict) else None
                    if not isinstance(entry_odds, (int, float)) or not math.isfinite(entry_odds):
                        entry_odds = None

                    # 3. Create Prediction object
                    prediction = Prediction(
                        match_id=match.id,
                        user_id=None,
                        home_prob=probabilities["home_prob"],
                        draw_prob=probabilities["draw_prob"],
                        away_prob=probabilities["away_prob"],
                        over_25_prob=optional_probabilities["over_25_prob"],
                        btts_prob=optional_probabilities["btts_prob"],
                        confidence=confidence_value,
                        bet_side=max(probabilities.items(), key=lambda item: item[1])[0].removesuffix("_prob"),
                        entry_odds=entry_odds,
                        timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
                    )

                    db.add(prediction)
                    generated_count += 1
                    logger.info(
                        "[prediction-agent] Generated prediction for %s vs %s via %s",
                        match.home_team,
                        match.away_team,
                        res.get("data_source", "unspecified"),
                    )

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
