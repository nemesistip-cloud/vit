# app/services/clv_tracker.py
import logging
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import CLVEntry, Match, Prediction
from app.services.market_utils import MarketUtils

logger = logging.getLogger(__name__)


class CLVTracker:
    """
    Closing Line Value Tracker - The truth metric for betting performance.

    CLV = (entry_odds - closing_odds) / closing_odds
    Positive CLV = you beat the closing line = true edge

    FIXED: Now tracks bet_side explicitly for accurate CLV calculation.
    """

    @staticmethod
    def calculate_clv(entry_odds: float, closing_odds: float) -> float:
        """Calculate Closing Line Value"""
        if closing_odds <= 0:
            return 0.0
        return (entry_odds - closing_odds) / closing_odds

    @staticmethod
    async def record_entry(
        db: AsyncSession,
        match_id: int,
        prediction_id: int,
        bet_side: str,
        entry_odds: float
    ) -> CLVEntry:
        """Record the odds when a bet was placed"""
        clv_entry = CLVEntry(
            match_id=match_id,
            prediction_id=prediction_id,
            bet_side=bet_side,
            entry_odds=entry_odds,
            closing_odds=None,
            clv=None
        )
        db.add(clv_entry)
        await db.commit()
        await db.refresh(clv_entry)

        logger.info(f"CLV entry recorded: match={match_id}, side={bet_side}, odds={entry_odds}")

        return clv_entry

    @staticmethod
    async def update_closing(
        db: AsyncSession,
        match_id: int,
        closing_odds_home: float,
        closing_odds_draw: float,
        closing_odds_away: float,
        actual_outcome: str,
        profit: float
    ) -> Optional[CLVEntry]:
        """Update closing odds and calculate final CLV after match"""
        # Find the CLV entry for this match
        result = await db.execute(
            select(CLVEntry).where(CLVEntry.match_id == match_id)
        )
        clv_entry = result.scalar_one_or_none()

        if not clv_entry:
            logger.warning(f"No CLV entry found for match {match_id}")
            return None

        # CRITICAL FIX: Use correct closing odds based on bet_side
        if clv_entry.bet_side == "home":
            closing_odds = closing_odds_home
        elif clv_entry.bet_side == "draw":
            closing_odds = closing_odds_draw
        elif clv_entry.bet_side == "away":
            closing_odds = closing_odds_away
        else:
            logger.warning(f"Unknown bet_side: {clv_entry.bet_side}")
            closing_odds = closing_odds_home  # Fallback

        # Calculate CLV
        clv_entry.closing_odds = closing_odds
        clv_entry.clv = CLVTracker.calculate_clv(clv_entry.entry_odds, closing_odds)
        clv_entry.bet_outcome = actual_outcome
        clv_entry.profit = profit

        # Remove the commit - let the caller handle transaction management
        # await db.commit()
        # await db.refresh(clv_entry)

        logger.info(f"CLV for match {match_id}: {clv_entry.clv:.4f} (side={clv_entry.bet_side})")

        return clv_entry

    @staticmethod
    async def update_closing_by_prediction(
        db: AsyncSession,
        prediction_id: int,
        closing_odds_home: float,
        closing_odds_draw: float,
        closing_odds_away: float,
        actual_outcome: str,
        profit: float
    ) -> Optional[CLVEntry]:
        """Update closing odds and calculate final CLV after match for a specific prediction"""
        # Find the CLV entry for this prediction
        result = await db.execute(
            select(CLVEntry).where(CLVEntry.prediction_id == prediction_id)
        )
        clv_entry = result.scalar_one_or_none()

        if not clv_entry:
            logger.warning(f"No CLV entry found for prediction {prediction_id}")
            return None

        # CRITICAL FIX: Use correct closing odds based on bet_side
        if clv_entry.bet_side == "home":
            closing_odds = closing_odds_home
        elif clv_entry.bet_side == "draw":
            closing_odds = closing_odds_draw
        elif clv_entry.bet_side == "away":
            closing_odds = closing_odds_away
        else:
            logger.warning(f"Unknown bet_side: {clv_entry.bet_side}")
            closing_odds = closing_odds_home  # Fallback

        # Calculate CLV
        clv_entry.closing_odds = closing_odds
        clv_entry.clv = CLVTracker.calculate_clv(clv_entry.entry_odds, closing_odds)
        clv_entry.bet_outcome = actual_outcome
        clv_entry.profit = profit

        logger.info(f"CLV for prediction {prediction_id}: {clv_entry.clv:.4f} (side={clv_entry.bet_side})")

        return clv_entry

    @staticmethod
    async def get_stats(db: AsyncSession) -> Dict:
        """Get aggregate CLV statistics"""
        result = await db.execute(
            select(CLVEntry.clv).where(CLVEntry.clv.isnot(None))
        )
        clvs = [row[0] for row in result.all() if row[0] is not None]

        if not clvs:
            return {"total_bets": 0, "avg_clv": 0, "positive_clv_rate": 0}

        positive_count = sum(1 for c in clvs if c > 0)

        return {
            "total_bets": len(clvs),
            "avg_clv": sum(clvs) / len(clvs),
            "positive_clv_rate": positive_count / len(clvs),
            "best_clv": max(clvs),
            "worst_clv": min(clvs)
        }

    @staticmethod
    async def get_stats_by_side(db: AsyncSession) -> Dict:
        """Get CLV statistics broken down by bet side"""
        result = await db.execute(
            select(CLVEntry.bet_side, CLVEntry.clv)
            .where(CLVEntry.clv.isnot(None))
        )
        rows = result.all()

        stats = {}
        for row in rows:
            side = row[0]
            clv = row[1]
            if side not in stats:
                stats[side] = {"clvs": [], "count": 0, "total": 0}
            stats[side]["clvs"].append(clv)
            stats[side]["count"] += 1
            stats[side]["total"] += clv

        result_dict = {}
        for side, data in stats.items():
            result_dict[side] = {
                "avg_clv": data["total"] / data["count"] if data["count"] > 0 else 0,
                "count": data["count"],
                "positive_rate": sum(1 for c in data["clvs"] if c > 0) / data["count"] if data["count"] > 0 else 0
            }

        return result_dict