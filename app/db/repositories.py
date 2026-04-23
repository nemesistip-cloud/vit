# app/db/repositories.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.db.models import Match, Prediction, CLVEntry, Edge, ModelPerformance, AIPrediction, AIPerformance, AISignalCache


class MatchRepository:
    """Data access layer for matches"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Match:
        """Create a new match"""
        match = Match(**kwargs)
        self.db.add(match)
        await self.db.flush()
        return match

    async def get_by_id(self, match_id: int) -> Optional[Match]:
        """Get match by ID"""
        result = await self.db.execute(select(Match).where(Match.id == match_id))
        return result.scalar_one_or_none()

    async def get_by_teams(self, home_team: str, away_team: str, limit: int = 10) -> List[Match]:
        """Get matches between two teams"""
        result = await self.db.execute(
            select(Match)
            .where(Match.home_team == home_team, Match.away_team == away_team)
            .order_by(Match.kickoff_time.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_result(self, match_id: int, **kwargs) -> Optional[Match]:
        """Update match result"""
        await self.db.execute(
            update(Match)
            .where(Match.id == match_id)
            .values(**kwargs, updated_at=datetime.now(timezone.utc))
        )
        await self.db.flush()
        return await self.get_by_id(match_id)

    async def get_upcoming(self, limit: int = 50) -> List[Match]:
        """Get upcoming matches"""
        result = await self.db.execute(
            select(Match)
            .where(Match.status == "scheduled")
            .where(Match.kickoff_time > datetime.now(timezone.utc))
            .order_by(Match.kickoff_time)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_completed(self, limit: int = 50) -> List[Match]:
        """Get completed matches"""
        result = await self.db.execute(
            select(Match)
            .where(Match.status == "completed")
            .order_by(Match.kickoff_time.desc())
            .limit(limit)
        )
        return result.scalars().all()


class PredictionRepository:
    """Data access layer for predictions"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Prediction:
        """Create a new prediction"""
        prediction = Prediction(**kwargs)
        self.db.add(prediction)
        await self.db.flush()
        return prediction

    async def get_by_id(self, prediction_id: int) -> Optional[Prediction]:
        """Get prediction by ID"""
        result = await self.db.execute(select(Prediction).where(Prediction.id == prediction_id))
        return result.scalar_one_or_none()

    async def get_by_match(self, match_id: int) -> Optional[Prediction]:
        """Get prediction for a match"""
        result = await self.db.execute(
            select(Prediction).where(Prediction.match_id == match_id)
        )
        return result.scalar_one_or_none()

    async def get_recent(self, limit: int = 20) -> List[Prediction]:
        """Get recent predictions"""
        result = await self.db.execute(
            select(Prediction)
            .order_by(Prediction.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Prediction]:
        """Get predictions in date range"""
        result = await self.db.execute(
            select(Prediction)
            .where(Prediction.timestamp.between(start_date, end_date))
            .order_by(Prediction.timestamp)
        )
        return result.scalars().all()

    async def update_stake(self, prediction_id: int, new_stake: float) -> Optional[Prediction]:
        """Update recommended stake"""
        await self.db.execute(
            update(Prediction)
            .where(Prediction.id == prediction_id)
            .values(recommended_stake=new_stake)
        )
        await self.db.flush()
        return await self.get_by_id(prediction_id)


class CLVRepository:
    """Data access layer for CLV entries"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> CLVEntry:
        """Create a new CLV entry"""
        clv_entry = CLVEntry(**kwargs)
        self.db.add(clv_entry)
        await self.db.flush()
        return clv_entry

    async def get_by_match(self, match_id: int) -> Optional[CLVEntry]:
        """Get CLV entry for a match"""
        result = await self.db.execute(select(CLVEntry).where(CLVEntry.match_id == match_id))
        return result.scalar_one_or_none()

    async def get_stats(self) -> Dict[str, Any]:
        """Get CLV statistics"""
        # Average CLV by bet side
        result = await self.db.execute(
            select(CLVEntry.bet_side, func.avg(CLVEntry.clv), func.count())
            .where(CLVEntry.clv.isnot(None))
            .group_by(CLVEntry.bet_side)
        )
        by_side = {}
        for row in result:
            by_side[row[0]] = {"avg_clv": float(row[1]) if row[1] else 0, "count": row[2]}

        # Overall stats
        overall = await self.db.execute(
            select(func.avg(CLVEntry.clv), func.count())
            .where(CLVEntry.clv.isnot(None))
        )
        overall_row = overall.first()

        return {
            "overall_avg_clv": float(overall_row[0]) if overall_row[0] else 0,
            "total_bets": overall_row[1] if overall_row[1] else 0,
            "by_bet_side": by_side
        }


class EdgeRepository:
    """Data access layer for edges"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Edge:
        """Create a new edge"""
        edge = Edge(**kwargs)
        self.db.add(edge)
        await self.db.flush()
        return edge

    async def get_by_id(self, edge_id: str) -> Optional[Edge]:
        """Get edge by ID"""
        result = await self.db.execute(select(Edge).where(Edge.edge_id == edge_id))
        return result.scalar_one_or_none()

    async def get_active(self, min_roi: float = 0.02, min_samples: int = 10) -> List[Edge]:
        """Get active edges with sufficient performance"""
        result = await self.db.execute(
            select(Edge)
            .where(Edge.status == "active")
            .where(Edge.roi >= min_roi)
            .where(Edge.sample_size >= min_samples)
            .order_by(Edge.roi.desc())
        )
        return result.scalars().all()

    async def update_performance(self, edge_id: str, roi: float, edge_value: float) -> Optional[Edge]:
        """Update edge performance metrics"""
        edge = await self.get_by_id(edge_id)
        if not edge:
            return None

        # Exponential moving average
        alpha = 1.0 / (edge.sample_size + 1)
        new_roi = edge.roi * (1 - alpha) + roi * alpha
        new_avg_edge = edge.avg_edge * (1 - alpha) + edge_value * alpha

        # Determine status based on ROI
        if new_roi < 0.005:
            status = "dead"
        elif new_roi < 0.01:
            status = "declining"
        else:
            status = "active"

        await self.db.execute(
            update(Edge)
            .where(Edge.edge_id == edge_id)
            .values(
                roi=new_roi,
                avg_edge=new_avg_edge,
                sample_size=edge.sample_size + 1,
                status=status,
                confidence=min(0.95, (edge.sample_size + 1) / 100),
                last_updated=datetime.now(timezone.utc)
    """Data access layer for AI predictions"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> AIPrediction:
        """Create a new AI prediction"""
        prediction = AIPrediction(**kwargs)
        self.db.add(prediction)
        await self.db.flush()
        return prediction

    async def get_by_match_and_source(self, match_id: int, source: str) -> Optional[AIPrediction]:
        """Get AI prediction by match and source"""
        result = await self.db.execute(
            select(AIPrediction)
            .where(AIPrediction.match_id == match_id)
            .where(AIPrediction.source == source)
        )
        return result.scalar_one_or_none()

    async def get_by_match(self, match_id: int) -> List[AIPrediction]:
        """Get all AI predictions for a match"""
        result = await self.db.execute(
            select(AIPrediction).where(AIPrediction.match_id == match_id)
        )
        return result.scalars().all()

    async def get_by_source(self, source: str, limit: int = 100) -> List[AIPrediction]:
        """Get AI predictions by source"""
        result = await self.db.execute(
            select(AIPrediction)
            .where(AIPrediction.source == source)
            .order_by(AIPrediction.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_performance(self, prediction_id: int, was_correct: bool, calibration_error: float):
        """Update performance metrics for a prediction"""
        await self.db.execute(
            update(AIPrediction)
            .where(AIPrediction.id == prediction_id)
            .values(
                was_correct=was_correct,
                calibration_error=calibration_error
            )
        )
        await self.db.flush()


class AIPerformanceRepository:
    """Data access layer for AI performance tracking"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, source: str) -> AIPerformance:
        """Get or create performance record for source"""
        result = await self.db.execute(
            select(AIPerformance).where(AIPerformance.source == source)
        )
        perf = result.scalar_one_or_none()

        if not perf:
            perf = AIPerformance(source=source)
            self.db.add(perf)
            await self.db.flush()

        return perf

    async def update_metrics(self, source: str, accuracy: float, calibration_score: float, sample_size: int):
        """Update performance metrics"""
        perf = await self.get_or_create(source)
        perf.accuracy = accuracy
        perf.calibration_score = calibration_score
        perf.sample_size = sample_size
        perf.total_predictions += sample_size
        perf.last_updated = datetime.now(timezone.utc)
        await self.db.flush()

    async def get_all(self) -> List[AIPerformance]:
        """Get all AI performance records"""
        result = await self.db.execute(select(AIPerformance))
        return result.scalars().all()

    async def update_weight(self, source: str, new_weight: float):
        """Update dynamic weight for source"""
        await self.db.execute(
            update(AIPerformance)
            .where(AIPerformance.source == source)
            .values(current_weight=new_weight, last_updated=datetime.now(timezone.utc))
        )
        await self.db.flush()


class AISignalCacheRepository:
    """Data access layer for AI signal cache"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_match(self, match_id: int) -> Optional[AISignalCache]:
        """Get cached signals for a match"""
        result = await self.db.execute(
            select(AISignalCache).where(AISignalCache.match_id == match_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update(self, match_id: int, **signals) -> AISignalCache:
        """Create or update signal cache for a match"""
        cache = await self.get_by_match(match_id)

        if cache:
            # Update existing
            for key, value in signals.items():
                if hasattr(cache, key):
                    setattr(cache, key, value)
            cache.timestamp = datetime.now(timezone.utc)
        else:
            # Create new
            cache = AISignalCache(match_id=match_id, **signals)
            self.db.add(cache)

        await self.db.flush()
        return cache

    async def get_multiple(self, match_ids: List[int]) -> List[AISignalCache]:
        """Get cached signals for multiple matches"""
        result = await self.db.execute(
            select(AISignalCache).where(AISignalCache.match_id.in_(match_ids))
        )
        return result.scalars().all()