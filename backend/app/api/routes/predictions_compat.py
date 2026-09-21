from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Prediction, Match
from app.api.deps import get_optional_user

router = APIRouter(prefix="/predictions", tags=["predictions-compat"])


@router.get("/match/{match_id}")
async def get_match_predictions(match_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_optional_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    pred_q = await db.execute(
        select(Prediction).where(Prediction.match_id == match_id).order_by(Prediction.timestamp.desc()).limit(1)
    )
    pred = pred_q.scalar_one_or_none()

    if not pred:
        return {"match_id": match_id, "bet_side": None, "confidence": None, "predictions": [], "consensus": None}

    models = pred.model_insights or []
    parsed_models = []
    for m in models:
        parsed_models.append({
            "model_name": m.get("model_name") or m.get("name"),
            "bet_side": m.get("bet_side") or None,
            "confidence": float(m.get("confidence") or 0.0),
            "final_ev": m.get("final_ev"),
            "entry_odds": m.get("entry_odds"),
            "reasoning": m.get("reason") or m.get("reasoning")
        })

    # Consensus — prefer stored model_consensus if present
    consensus = pred.model_consensus
    if not consensus:
        votes = {"home": 0, "draw": 0, "away": 0}
        for m in parsed_models:
            side = m.get("bet_side")
            if side in votes:
                votes[side] += 1
        total = sum(votes.values()) or 1
        consensus = {
            "home_pct": round(votes["home"] / total * 100, 1),
            "draw_pct": round(votes["draw"] / total * 100, 1),
            "away_pct": round(votes["away"] / total * 100, 1),
            "recommended": pred.bet_side or None,
        }

    return {
        "match_id": match_id,
        "bet_side": pred.bet_side,
        "confidence": float(pred.confidence or 0.0),
        "final_ev": float(pred.final_ev or 0.0) if getattr(pred, 'final_ev', None) is not None else None,
        "entry_odds": float(pred.entry_odds) if getattr(pred, 'entry_odds', None) is not None else None,
        "predictions": parsed_models,
        "consensus": consensus,
    }
