"""AI Signals Service - Feature engineering from AI predictions"""

import logging
from typing import Dict, List, Optional
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import AISignalCache, AIPrediction, AIPerformance

logger = logging.getLogger(__name__)


class AISignalService:
    """Generate features from AI predictions for model input"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_signals_for_match(self, match_id: int) -> Dict:
        """Get all AI signals for a specific match"""
        result = await self.db.execute(
            select(AISignalCache).where(AISignalCache.match_id == match_id)
        )
        cache = result.scalar_one_or_none()

        if not cache:
            return self._empty_signals()

        return {
            # Consensus signals
            "ai_consensus_home": cache.consensus_home,
            "ai_consensus_draw": cache.consensus_draw,
            "ai_consensus_away": cache.consensus_away,

            # Disagreement (information asymmetry)
            "ai_disagreement": cache.disagreement_score,
            "ai_high_disagreement": 1 if cache.disagreement_score > 0.05 else 0,

            # Confidence signals
            "ai_max_confidence": cache.max_confidence,
            "ai_avg_confidence": self._avg_confidence(cache.per_ai_predictions),

            # Weighted probabilities
            "ai_weighted_home": cache.weighted_home,
            "ai_weighted_draw": cache.weighted_draw,
            "ai_weighted_away": cache.weighted_away,

            # Per-AI signals (if needed for ensemble)
            "ai_chatgpt_home": self._get_ai_prob(cache, "chatgpt", "home"),
            "ai_chatgpt_draw": self._get_ai_prob(cache, "chatgpt", "draw"),
            "ai_chatgpt_away": self._get_ai_prob(cache, "chatgpt", "away"),
            "ai_gemini_home": self._get_ai_prob(cache, "gemini", "home"),
            "ai_gemini_draw": self._get_ai_prob(cache, "gemini", "draw"),
            "ai_gemini_away": self._get_ai_prob(cache, "gemini", "away"),
            "ai_grok_home": self._get_ai_prob(cache, "grok", "home"),
            "ai_deepseek_home": self._get_ai_prob(cache, "deepseek", "home"),
            "ai_perplexity_home": self._get_ai_prob(cache, "perplexity", "home"),
        }

    async def get_all_signals(self, match_ids: List[int]) -> Dict[int, Dict]:
        """Get AI signals for multiple matches"""
        result = await self.db.execute(
            select(AISignalCache).where(AISignalCache.match_id.in_(match_ids))
        )
        caches = result.scalars().all()

        signals = {}
        for cache in caches:
            signals[cache.match_id] = {
                "ai_consensus_home": cache.consensus_home,
                "ai_consensus_draw": cache.consensus_draw,
                "ai_consensus_away": cache.consensus_away,
                "ai_disagreement": cache.disagreement_score,
                "ai_max_confidence": cache.max_confidence,
                "ai_weighted_home": cache.weighted_home,
                "ai_weighted_draw": cache.weighted_draw,
                "ai_weighted_away": cache.weighted_away,
            }

        return signals

    def _empty_signals(self) -> Dict:
        """Return neutral signals when no AI data available"""
        return {
            "ai_consensus_home": 0.34,
            "ai_consensus_draw": 0.33,
            "ai_consensus_away": 0.33,
            "ai_disagreement": 0.0,
            "ai_high_disagreement": 0,
            "ai_max_confidence": 0.5,
            "ai_avg_confidence": 0.5,
            "ai_weighted_home": 0.34,
            "ai_weighted_draw": 0.33,
            "ai_weighted_away": 0.33,
        }

    def _avg_confidence(self, per_ai: Dict) -> float:
        """Calculate average confidence across AIs"""
        confidences = [p.get("confidence", 0.5) for p in per_ai.values()]
        return sum(confidences) / len(confidences) if confidences else 0.5

    def _get_ai_prob(self, cache: AISignalCache, source: str, outcome: str) -> float:
        """Get specific AI's probability for an outcome"""
        per_ai = cache.per_ai_predictions
        if source in per_ai:
            return per_ai[source].get(outcome, 0.33)
        return 0.33

    async def calculate_ai_vs_model_gap(self, match_id: int, model_probs: Dict) -> float:
        """Calculate gap between AI consensus and model prediction"""
        signals = await self.get_signals_for_match(match_id)

        ai_consensus = {
            "home": signals["ai_consensus_home"],
            "draw": signals["ai_consensus_draw"],
            "away": signals["ai_consensus_away"]
        }

        # Find outcome with largest disagreement
        gaps = {
            outcome: abs(ai_consensus[outcome] - model_probs.get(outcome, 0.33))
            for outcome in ["home", "draw", "away"]
        }

        return max(gaps.values())