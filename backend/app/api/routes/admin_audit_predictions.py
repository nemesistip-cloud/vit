import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Match, Prediction
from app.auth.dependencies import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/audit-predictions")
async def audit_all_predictions(
    sport: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin),
):
    """
    Read-only audit of persisted predictions across upcoming matches.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Fetch upcoming matches
    query = select(Match).where(
        Match.status == "scheduled",
        Match.kickoff_time >= now
    ).order_by(Match.kickoff_time.asc()).limit(limit)

    if sport:
        query = query.where(Match.sport == sport)

    result = await db.execute(query)
    matches = result.scalars().all()

    if not matches:
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc),
            "total_audited": 0,
            "message": "No upcoming matches found for audit",
            "results": [],
        }

    audit_results = []

    for match in matches:
        match_report = {
            "match_id": match.id,
            "teams": f"{match.home_team} vs {match.away_team}",
            "sport": match.sport,
            "kickoff": match.kickoff_time,
            "prediction_status": "missing",
            "markets": {
                "1x2": False,
                "over_under": False,
                "btts": False,
                "asian_handicap": False,
                "correct_score": False
            },
            "errors": []
        }

        # Check existing predictions
        pred_query = select(Prediction).where(Prediction.match_id == match.id).order_by(Prediction.timestamp.desc())
        pred_result = await db.execute(pred_query)
        prediction = pred_result.scalars().first()

        if prediction:
            state = str(prediction.status or "unknown").lower()
            match_report["prediction_status"] = "present" if state == "ready" else state
            match_report["markets"]["1x2"] = all(
                value is not None
                for value in (prediction.home_prob, prediction.draw_prob, prediction.away_prob)
            )
            match_report["markets"]["over_under"] = prediction.over_25_prob is not None
            match_report["markets"]["btts"] = prediction.btts_prob is not None
            match_report["markets"]["asian_handicap"] = prediction.ah_line is not None
            match_report["markets"]["correct_score"] = prediction.cs_probs is not None
            if prediction.error_message:
                match_report["errors"].append(prediction.error_message)
        else:
            match_report["errors"].append("No persisted prediction is available; this audit did not generate one.")

        audit_results.append(match_report)

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc),
        "total_audited": len(audit_results),
        "results": audit_results
    }
