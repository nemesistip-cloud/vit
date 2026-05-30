"""AI Profiler Service - Performance tracking and dynamic weighting"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.db.models import AIPerformance, AIPrediction, Match

logger = logging.getLogger(__name__)


class AIProfilerService:
    """Track and analyze AI prediction performance"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_weights(self):
        """Update dynamic weights based on recent performance"""
        result = await self.db.execute(select(AIPerformance))
        performances = result.scalars().all()

        for perf in performances:
            # Weight based on accuracy and calibration
            base_weight = (perf.accuracy * 0.7) + (perf.calibration_score * 0.3)

            # Minimum weight threshold
            min_weight = 0.1
            new_weight = max(base_weight, min_weight)

            # Decay weight if sample size is small
            if perf.sample_size < 10:
                new_weight *= 0.8

            perf.current_weight = new_weight
            perf.last_updated = datetime.now()

        await self.db.commit()
        logger.info(f"Updated weights for {len(performances)} AI sources")

    async def get_weighted_ensemble(self, match_id: int) -> Dict:
        """Get weighted ensemble prediction for a match"""
        result = await self.db.execute(
            select(AIPrediction, AIPerformance)
            .join(AIPerformance, AIPrediction.source == AIPerformance.source)
            .where(AIPrediction.match_id == match_id)
        )

        predictions = result.all()
        if not predictions:
            return {"home": 0.33, "draw": 0.33, "away": 0.33}

        total_weight = sum(perf.current_weight for _, perf in predictions)

        if total_weight == 0:
            return {"home": 0.33, "draw": 0.33, "away": 0.33}

        weighted_home = sum(pred.home_prob * perf.current_weight for pred, perf in predictions) / total_weight
        weighted_draw = sum(pred.draw_prob * perf.current_weight for pred, perf in predictions) / total_weight
        weighted_away = sum(pred.away_prob * perf.current_weight for pred, perf in predictions) / total_weight

        return {
            "home": weighted_home,
            "draw": weighted_draw,
            "away": weighted_away
        }

    async def analyze_bias(self, source: str, league: str = None) -> Dict:
        """Analyze bias patterns for an AI source"""
        query = select(AIPrediction, Match).join(Match, AIPrediction.match_id == Match.id)

        if league:
            query = query.where(Match.league == league)

        result = await self.db.execute(query)
        predictions = result.all()

        if not predictions:
            return {}

        home_overrates = []
        draw_overrates = []
        away_overrates = []

        for pred, match in predictions:
            if match.actual_outcome and match.home_goals is not None:
                # Calculate actual probabilities from results
                total_matches = len(predictions)
                home_wins = sum(1 for p, m in predictions if m.actual_outcome == "home")
                draws = sum(1 for p, m in predictions if m.actual_outcome == "draw")
                away_wins = sum(1 for p, m in predictions if m.actual_outcome == "away")

                actual_home_prob = home_wins / total_matches if total_matches > 0 else 0.33
                actual_draw_prob = draws / total_matches if total_matches > 0 else 0.33
                actual_away_prob = away_wins / total_matches if total_matches > 0 else 0.33

                home_overrates.append(pred.home_prob - actual_home_prob)
                draw_overrates.append(pred.draw_prob - actual_draw_prob)
                away_overrates.append(pred.away_prob - actual_away_prob)

        return {
            "source": source,
            "league": league,
            "sample_size": len(predictions),
            "bias_home_overrate": sum(home_overrates) / len(home_overrates) if home_overrates else 0,
            "bias_draw_overrate": sum(draw_overrates) / len(draw_overrates) if draw_overrates else 0,
            "bias_away_overrate": sum(away_overrates) / len(away_overrates) if away_overrates else 0,
        }

    async def get_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        result = await self.db.execute(select(AIPerformance))
        performances = result.scalars().all()

        report = {
            "generated_at": datetime.now(),
            "ai_sources": len(performances),
            "sources": []
        }

        for perf in performances:
            # Get recent predictions (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_result = await self.db.execute(
                select(func.count(AIPrediction.id))
                .where(AIPrediction.source == perf.source)
                .where(AIPrediction.timestamp >= thirty_days_ago)
            )
            recent_count = recent_result.scalar()

            report["sources"].append({
                "source": perf.source,
                "accuracy": perf.accuracy,
                "calibration_score": perf.calibration_score,
                "sample_size": perf.sample_size,
                "current_weight": perf.current_weight,
                "recent_predictions": recent_count,
                "certified": perf.certified
            })

        return report

    async def detect_drift(self, source: str, window_days: int = 30) -> Dict:
        """Detect performance drift over time"""
        cutoff_date = datetime.now() - timedelta(days=window_days)

        # Get predictions in windows
        result = await self.db.execute(
            select(AIPrediction)
            .where(AIPrediction.source == source)
            .where(AIPrediction.timestamp >= cutoff_date)
            .order_by(AIPrediction.timestamp)
        )
        predictions = result.scalars().all()

        if len(predictions) < 10:
            return {"drift_detected": False, "reason": "Insufficient data"}

        # Split into two halves
        mid_point = len(predictions) // 2
        first_half = predictions[:mid_point]
        second_half = predictions[mid_point:]

        # Calculate accuracies
        def calc_accuracy(preds):
            correct = sum(1 for p in preds if p.was_correct)
            return correct / len(preds) if preds else 0

        first_accuracy = calc_accuracy(first_half)
        second_accuracy = calc_accuracy(second_half)

        drift_threshold = 0.1  # 10% change
        drift_detected = abs(first_accuracy - second_accuracy) > drift_threshold

        return {
            "drift_detected": drift_detected,
            "first_half_accuracy": first_accuracy,
            "second_half_accuracy": second_accuracy,
            "drift_magnitude": abs(first_accuracy - second_accuracy),
            "sample_sizes": [len(first_half), len(second_half)]
        }