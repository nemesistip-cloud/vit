"""AI Signals Service — Native Feature Engineering.
Replaces external AI provider signals with native analytics features.
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import AISignalCache

logger = logging.getLogger(__name__)

class AISignalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_signals_for_match(self, match_id: int) -> Dict:
        result = await self.db.execute(
            select(AISignalCache).where(AISignalCache.match_id == match_id)
        )
        cache = result.scalar_one_or_none()
        if not cache:
            return self._empty_signals()

        return {
            "ai_consensus_home": cache.consensus_home,
            "ai_consensus_draw": cache.consensus_draw,
            "ai_consensus_away": cache.consensus_away,
            "ai_disagreement": cache.disagreement_score,
            "ai_high_disagreement": 1 if cache.disagreement_score > 0.05 else 0,
            "ai_max_confidence": cache.max_confidence,
            "ai_avg_confidence": 0.75,
            "ai_weighted_home": cache.weighted_home,
            "ai_weighted_draw": cache.weighted_draw,
            "ai_weighted_away": cache.weighted_away,
            # Native provider signals
            "ai_native_home": cache.consensus_home,
            "ai_native_draw": cache.consensus_draw,
            "ai_native_away": cache.consensus_away,
        }

    async def get_all_signals(self, match_ids: List[int]) -> Dict[int, Dict]:
        result = await self.db.execute(
            select(AISignalCache).where(AISignalCache.match_id.in_(match_ids))
        )
        caches = result.scalars().all()
        return {c.match_id: {"ai_consensus_home": c.consensus_home, "ai_consensus_draw": c.consensus_draw, "ai_consensus_away": c.consensus_away} for c in caches}

    def _empty_signals(self) -> Dict:
        return {"ai_consensus_home": 0.34, "ai_consensus_draw": 0.33, "ai_consensus_away": 0.33, "ai_disagreement": 0.0, "ai_high_disagreement": 0}

    async def calculate_ai_vs_model_gap(self, match_id: int, model_probs: Dict) -> float:
        return 0.0
