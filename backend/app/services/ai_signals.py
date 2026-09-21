"""AI Signals Service — Native Feature Engineering.
Replaces external AI provider signals with native analytics features and delegates to RecommendationEngine.
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.models import AISignalCache, Match, Prediction
from app.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

class AISignalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = RecommendationEngine(db=db)

    async def get_signals_for_match(self, match_id: int) -> Dict:
        result = await self.db.execute(
            select(AISignalCache).where(AISignalCache.match_id == match_id)
        )
        cache = result.scalar_one_or_none()
        if cache:
            meta = cache.per_ai_predictions or {}
            return {
                "ai_consensus_home": cache.consensus_home,
                "ai_consensus_draw": cache.consensus_draw,
                "ai_consensus_away": cache.consensus_away,
                "ai_disagreement": cache.disagreement_score,
                "ai_high_disagreement": 1 if cache.disagreement_score > 0.05 else 0,
                "ai_max_confidence": cache.max_confidence,
                "ai_avg_confidence": cache.max_confidence,
                "ai_weighted_home": cache.weighted_home,
                "ai_weighted_draw": cache.weighted_draw,
                "ai_weighted_away": cache.weighted_away,
                "ai_native_home": cache.consensus_home,
                "ai_native_draw": cache.consensus_draw,
                "ai_native_away": cache.consensus_away,
                "signal_score": meta.get("signal_score", 50.0),
                "signal_state": meta.get("signal_state", "QUALIFIED_SIGNAL"),
                "best_side": meta.get("best_side", "home"),
                "vig_free_edge": meta.get("vig_free_edge", 0.0),
                "market_type": meta.get("market_type", "sports"),
                "calibration": meta.get("calibration", {}),
            }

        # On cache miss, attempt to evaluate from Match + Prediction table
        match_stmt = select(Match).where(Match.id == match_id)
        match_res = await self.db.execute(match_stmt)
        match = match_res.scalar_one_or_none()
        if not match:
            return self._empty_signals()

        pred_stmt = select(Prediction).where(Prediction.match_id == match_id).order_by(desc(Prediction.timestamp)).limit(1)
        pred_res = await self.db.execute(pred_stmt)
        pred = pred_res.scalar_one_or_none()

        hp = float(pred.home_prob or 0.333) if pred else 0.333
        dp = float(pred.draw_prob or 0.333) if pred else 0.333
        ap = float(pred.away_prob or 0.334) if pred else 0.334

        market_odds = {
            "home": match.opening_odds_home or 2.5,
            "draw": match.opening_odds_draw or 3.2,
            "away": match.opening_odds_away or 2.8,
        }
        individual_results = pred.model_insights if pred and isinstance(pred.model_insights, list) else []

        rec = self.engine.generate_recommendation(
            match_id=match_id,
            home_team=match.home_team,
            away_team=match.away_team,
            market_type=match.market_type or "sports",
            category=match.sport or "football",
            home_prob=hp,
            draw_prob=dp,
            away_prob=ap,
            market_odds=market_odds,
            individual_results=individual_results,
        )

        await self.engine.save_signal_history(match_id, rec)

        sig_metrics = rec["signal_metrics"]
        best_sel = rec["best_selection"]

        return {
            "ai_consensus_home": hp,
            "ai_consensus_draw": dp,
            "ai_consensus_away": ap,
            "ai_disagreement": rec["model_consensus"]["disagreement_score"],
            "ai_high_disagreement": 1 if rec["model_consensus"]["disagreement_score"] > 0.05 else 0,
            "ai_max_confidence": sig_metrics["confidence"],
            "ai_avg_confidence": sig_metrics["confidence"],
            "ai_weighted_home": hp,
            "ai_weighted_draw": dp,
            "ai_weighted_away": ap,
            "ai_native_home": hp,
            "ai_native_draw": dp,
            "ai_native_away": ap,
            "signal_score": sig_metrics["signal_score"],
            "signal_state": sig_metrics["signal_state"],
            "best_side": best_sel["side"],
            "vig_free_edge": best_sel["vig_free_edge"],
            "market_type": rec["market_type"],
            "calibration": rec["calibration"],
        }

    async def get_all_signals(self, match_ids: List[int]) -> Dict[int, Dict]:
        result = await self.db.execute(
            select(AISignalCache).where(AISignalCache.match_id.in_(match_ids))
        )
        caches = result.scalars().all()
        return {
            c.match_id: {
                "ai_consensus_home": c.consensus_home,
                "ai_consensus_draw": c.consensus_draw,
                "ai_consensus_away": c.consensus_away,
                "ai_disagreement": c.disagreement_score,
                "ai_max_confidence": c.max_confidence,
            }
            for c in caches
        }

    def _empty_signals(self) -> Dict:
        return {
            "ai_consensus_home": 0.34,
            "ai_consensus_draw": 0.33,
            "ai_consensus_away": 0.33,
            "ai_disagreement": 0.0,
            "ai_high_disagreement": 0,
            "signal_score": 0.0,
            "signal_state": "DATA_DEFICIENT",
            "best_side": "home",
            "vig_free_edge": 0.0,
        }

    async def calculate_ai_vs_model_gap(self, match_id: int, model_probs: Dict) -> float:
        signals = await self.get_signals_for_match(match_id)
        if not signals:
            return 0.0
        ai_home = signals.get("ai_consensus_home", 0.333)
        model_home = model_probs.get("home", 0.333)
        return round(abs(ai_home - model_home), 4)
