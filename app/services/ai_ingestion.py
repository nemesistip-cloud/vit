"""AI Ingestion Service - Manual import of AI predictions"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.models import AIPrediction, AIPerformance, Match

logger = logging.getLogger(__name__)


class AIIngestionService:
    """Handle manual ingestion and management of AI predictions"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_prediction(self, match_id: int, source: str, home_prob: float,
                              draw_prob: float, away_prob: float, confidence: float = 0.7,
                              reason: str = None, raw_content: str = None,
                              submitted_by: int = None) -> bool:
        """Ingest a single AI prediction (supports raw analysis text + submitter)."""

        # Validate probabilities
        total = home_prob + draw_prob + away_prob
        if total <= 0:
            return False
        if abs(total - 1.0) > 0.01:
            # Normalize
            home_prob /= total
            draw_prob /= total
            away_prob /= total

        # Check if exists
        existing = await self.db.execute(
            select(AIPrediction).where(
                AIPrediction.match_id == match_id,
                AIPrediction.source == source
            )
        )
        pred = existing.scalar_one_or_none()

        if pred:
            # Update
            pred.home_prob = home_prob
            pred.draw_prob = draw_prob
            pred.away_prob = away_prob
            pred.confidence = confidence
            pred.reason = reason
            if raw_content is not None:
                pred.raw_content = raw_content
            if submitted_by is not None:
                pred.submitted_by = submitted_by
            pred.timestamp = datetime.now()
        else:
            # Create
            pred = AIPrediction(
                match_id=match_id,
                source=source,
                home_prob=home_prob,
                draw_prob=draw_prob,
                away_prob=away_prob,
                confidence=confidence,
                reason=reason,
                raw_content=raw_content,
                submitted_by=submitted_by,
            )
            self.db.add(pred)

        await self.db.commit()
        return True

    async def get_predictions_for_match(self, match_id: int) -> List[Dict]:
        """Get all AI predictions for a match"""
        result = await self.db.execute(
            select(AIPrediction).where(AIPrediction.match_id == match_id)
        )
        predictions = result.scalars().all()

        return [{
            "source": p.source,
            "home_prob": p.home_prob,
            "draw_prob": p.draw_prob,
            "away_prob": p.away_prob,
            "confidence": p.confidence,
            "reason": p.reason,
            "timestamp": p.timestamp
        } for p in predictions]

    async def update_performance_metrics(self):
        """Update AI performance metrics after matches complete"""
        # Get completed matches with AI predictions
        result = await self.db.execute(
            select(Match, AIPrediction)
            .join(AIPrediction, Match.id == AIPrediction.match_id)
            .where(Match.status == "completed")
            .where(AIPrediction.was_correct.is_(None))  # Not yet evaluated
        )

        updates = {}
        for match, pred in result:
            actual_outcome = match.actual_outcome
            if not actual_outcome:
                continue

            # Determine if correct
            predicted_probs = {
                "home": pred.home_prob,
                "draw": pred.draw_prob,
                "away": pred.away_prob
            }
            predicted_outcome = max(predicted_probs, key=predicted_probs.get)
            was_correct = predicted_outcome == actual_outcome

            # Calibration error (Brier score component)
            actual_prob = predicted_probs.get(actual_outcome, 0)
            calibration_error = (1 - actual_prob) ** 2

            # Update prediction
            await self.db.execute(
                update(AIPrediction)
                .where(AIPrediction.id == pred.id)
                .values(
                    was_correct=was_correct,
                    calibration_error=calibration_error
                )
            )

            # Track for performance update
            source = pred.source
            if source not in updates:
                updates[source] = {"correct": 0, "total": 0, "calibration_errors": []}
            updates[source]["total"] += 1
            if was_correct:
                updates[source]["correct"] += 1
            updates[source]["calibration_errors"].append(calibration_error)

        # Update performance records
        for source, metrics in updates.items():
            accuracy = metrics["correct"] / metrics["total"] if metrics["total"] > 0 else 0
            calibration_score = 1 - (sum(metrics["calibration_errors"]) / len(metrics["calibration_errors"])) if metrics["calibration_errors"] else 0

            # Get or create performance record
            perf_result = await self.db.execute(
                select(AIPerformance).where(AIPerformance.source == source)
            )
            perf = perf_result.scalar_one_or_none()

            if perf:
                perf.accuracy = accuracy
                perf.calibration_score = calibration_score
                perf.sample_size += metrics["total"]
                perf.total_predictions += metrics["total"]
                perf.last_updated = datetime.now()
            else:
                perf = AIPerformance(
                    source=source,
                    accuracy=accuracy,
                    calibration_score=calibration_score,
                    sample_size=metrics["total"],
                    total_predictions=metrics["total"]
                )
                self.db.add(perf)

        await self.db.commit()
        logger.info(f"Updated performance for {len(updates)} AI sources")

    async def get_ai_performance(self, source: str = None) -> Dict:
        """Get performance metrics for AI sources"""
        if source:
            result = await self.db.execute(
                select(AIPerformance).where(AIPerformance.source == source)
            )
            perf = result.scalar_one_or_none()
            if not perf:
                return {}
            return {
                "source": perf.source,
                "accuracy": perf.accuracy,
                "calibration_score": perf.calibration_score,
                "sample_size": perf.sample_size,
                "current_weight": perf.current_weight
            }
        else:
            # All sources
            result = await self.db.execute(select(AIPerformance))
            performances = result.scalars().all()
            return {p.source: {
                "accuracy": p.accuracy,
                "calibration_score": p.calibration_score,
                "sample_size": p.sample_size,
                "current_weight": p.current_weight
            } for p in performances}