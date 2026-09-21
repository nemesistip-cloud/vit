import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Match, Prediction
from app.auth.dependencies import get_current_admin
from app.core.dependencies import get_orchestrator
from app.schemas.schemas import MatchRequest

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
    Diagnostic tool to audit predictions across all sports.
    Iterates through upcoming matches and attempts to generate/verify predictions.
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
        return {"status": "ok", "message": "No upcoming matches found for audit", "results": []}

    orchestrator = get_orchestrator()
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
            match_report["prediction_status"] = "present"
            match_report["markets"]["1x2"] = all([prediction.home_prob, prediction.draw_prob, prediction.away_prob])
            match_report["markets"]["over_under"] = prediction.over_25_prob is not None
            match_report["markets"]["btts"] = prediction.btts_prob is not None
            match_report["markets"]["asian_handicap"] = prediction.ah_line is not None
            match_report["markets"]["correct_score"] = prediction.cs_probs is not None
        else:
            # Try to trigger a prediction if missing (dry run via orchestrator)
            if orchestrator:
                try:
                    # Mock features for diagnostic
                    features = {
                        "home_team": match.home_team,
                        "away_team": match.away_team,
                        "league": match.league,
                        "sport": match.sport,
                        "market_odds": {
                            "home": match.opening_odds_home or 2.0,
                            "draw": match.opening_odds_draw or 3.0,
                            "away": match.opening_odds_away or 3.5
                        }
                    }

                    # For football, use the full orchestrator
                    if match.sport == "football":
                        # We don't want to save to DB, just test the engine
                        res = orchestrator.predict_ensemble(features)
                        if res and "predictions" in res:
                            p = res["predictions"]
                            match_report["prediction_status"] = "test_success"
                            match_report["markets"]["1x2"] = True
                            match_report["markets"]["over_under"] = p.get("over_25_prob") is not None
                            match_report["markets"]["btts"] = p.get("btts_prob") is not None
                            match_report["markets"]["asian_handicap"] = p.get("ah_line") is not None
                            match_report["markets"]["correct_score"] = p.get("cs_probs") is not None
                    else:
                        match_report["prediction_status"] = "placeholder_only"
                        match_report["errors"].append(f"Sport '{match.sport}' lacks non-placeholder implementation")

                except Exception as e:
                    match_report["prediction_status"] = "test_failed"
                    match_report["errors"].append(str(e))
            else:
                match_report["prediction_status"] = "orchestrator_unavailable"

        audit_results.append(match_report)

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc),
        "total_audited": len(audit_results),
        "results": audit_results
    }
