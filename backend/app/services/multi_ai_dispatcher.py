"""app/services/multi_ai_dispatcher.py — Native AI Dispatcher.
Routes requests to the internal ensemble and returns real DB-backed predictions.
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

logger = logging.getLogger(__name__)

PROVIDERS = ["native"]


async def run_multi_ai(
    match_id: int,
    db: AsyncSession,
    sources: List[str] = None,
) -> Dict[str, Any]:
    """
    Run native analytics for a match.
    Queries real AIPrediction records from DB, falling back to the
    Prediction table (model-generated), then to neutral defaults.
    """
    from app.db.models import AIPrediction, Prediction, Match

    match = (await db.execute(
        select(Match).where(Match.id == match_id)
    )).scalar_one_or_none()
    if not match:
        raise ValueError(f"Match {match_id} not found")

    # 1. Try AI Prediction records (manually ingested / past runs)
    ai_preds_q = await db.execute(
        select(AIPrediction)
        .where(AIPrediction.match_id == match_id)
        .order_by(desc(AIPrediction.timestamp))
    )
    ai_preds = ai_preds_q.scalars().all()

    if ai_preds:
        weights = [p.confidence or 0.7 for p in ai_preds]
        total_w = sum(weights) or 1.0
        home_prob = sum(p.home_prob * w for p, w in zip(ai_preds, weights)) / total_w
        draw_prob = sum(p.draw_prob * w for p, w in zip(ai_preds, weights)) / total_w
        away_prob = sum(p.away_prob * w for p, w in zip(ai_preds, weights)) / total_w
        confidence = sum(weights) / len(weights)
        sources_used = list({p.source for p in ai_preds})
        reason = f"Weighted ensemble from {len(ai_preds)} AI prediction(s): {', '.join(sources_used)}."
        return _build_result(match_id, home_prob, draw_prob, away_prob, confidence, reason, ai_preds)

    # 2. Fall back to model-generated Prediction table
    pred = (await db.execute(
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(desc(Prediction.timestamp))
        .limit(1)
    )).scalar_one_or_none()

    if pred and pred.home_prob:
        home_prob = float(pred.home_prob)
        draw_prob = float(pred.draw_prob or 0)
        away_prob = float(pred.away_prob or 0)
        confidence = float(pred.confidence or 0.6)
        reason = f"Ensemble model prediction (confidence {confidence:.0%}). Bet side: {pred.bet_side or 'home'}."
        return _build_result(match_id, home_prob, draw_prob, away_prob, confidence, reason)

    # 3. No data — compute from odds if available
    home_prob, draw_prob, away_prob = _from_odds(match)
    confidence = 0.5
    reason = "Vig-free market probability computed from available odds."
    return _build_result(match_id, home_prob, draw_prob, away_prob, confidence, reason)


def _from_odds(match) -> tuple:
    """Compute vig-free probabilities from match odds."""
    try:
        h = float(match.opening_odds_home or match.closing_odds_home or 0)
        d = float(match.opening_odds_draw or match.closing_odds_draw or 0)
        a = float(match.opening_odds_away or match.closing_odds_away or 0)
        if h > 0 and d > 0 and a > 0:
            raw_h, raw_d, raw_a = 1 / h, 1 / d, 1 / a
            total = raw_h + raw_d + raw_a
            return raw_h / total, raw_d / total, raw_a / total
    except Exception:
        pass
    return 0.34, 0.33, 0.33


def _build_result(
    match_id: int,
    home_prob: float,
    draw_prob: float,
    away_prob: float,
    confidence: float,
    reason: str,
    ai_preds: Optional[list] = None,
) -> Dict[str, Any]:
    total = home_prob + draw_prob + away_prob
    if total > 0 and abs(total - 1.0) > 0.01:
        home_prob /= total
        draw_prob /= total
        away_prob /= total

    leader = max(
        {"home": home_prob, "draw": draw_prob, "away": away_prob},
        key={"home": home_prob, "draw": draw_prob, "away": away_prob}.get
    )
    sources_breakdown = []
    if ai_preds:
        for p in ai_preds:
            sources_breakdown.append({
                "source": p.source,
                "home_prob": round(float(p.home_prob), 4),
                "draw_prob": round(float(p.draw_prob), 4),
                "away_prob": round(float(p.away_prob), 4),
                "confidence": round(float(p.confidence or 0.7), 4),
            })

    return {
        "match_id": match_id,
        "results": {
            "native": {
                "available": True,
                "home_prob": round(home_prob, 4),
                "draw_prob": round(draw_prob, 4),
                "away_prob": round(away_prob, 4),
                "confidence": round(confidence, 4),
                "leader": leader,
                "reason": reason,
                "sources_breakdown": sources_breakdown,
            }
        }
    }
