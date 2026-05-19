"""app/modules/academy/routes.py
Academy Layer — Certification, bootcamps, and guild incubator.

Progress and certification status are derived from the user's real prediction
record and task completion history.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Prediction
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/academy", tags=["Academy"])

_TRACKS = {
    "analyst":   {"name": "VIT Certified Prediction Analyst",   "min_preds": 50, "min_accuracy": 0.60},
    "validator": {"name": "VIT Certified Validator",            "min_preds": 100, "min_accuracy": 0.65},
    "strategist":{"name": "VIT Certified Strategist",           "min_preds": 200, "min_accuracy": 0.70},
}
_DEFAULT_TRACK = "analyst"


@router.post("/enroll")
async def enroll_academy(
    track: str = _DEFAULT_TRACK,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enroll the current user in an Academy certification track."""
    track_cfg = _TRACKS.get(track)
    if not track_cfg:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown track '{track}'. Valid: {', '.join(_TRACKS.keys())}",
        )

    total = (
        await db.execute(
            select(func.count(Prediction.id)).where(Prediction.user_id == current_user.id)
        )
    ).scalar() or 0

    return {
        "status":         "enrolled",

        "user_id":        current_user.id,
        "track":          track,
        "track_name":     track_cfg["name"],
        "next_step":      f"{track_cfg['name']} — Module 1",
        "requirements":   {
            "min_predictions": track_cfg["min_preds"],
            "min_accuracy":    track_cfg["min_accuracy"],
        },
        "your_predictions": total,
        "enrolled_at":    datetime.now(timezone.utc).isoformat(),
    }


@router.get("/certification/status")
async def get_cert_status(
    track: str = _DEFAULT_TRACK,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return real certification progress based on prediction history."""
    track_cfg = _TRACKS.get(track, _TRACKS[_DEFAULT_TRACK])

    from app.db.models import Match
    from sqlalchemy import join as sqljoin

    total = (
        await db.execute(
            select(func.count(Prediction.id)).where(Prediction.user_id == current_user.id)
        )
    ).scalar() or 0

    # Correct = bet_side matches actual_outcome on settled matches
    correct = (
        await db.execute(
            select(func.count(Prediction.id))
            .select_from(
                sqljoin(Prediction, Match, Prediction.match_id == Match.id)
            )
            .where(
                Prediction.user_id == current_user.id,
                Match.actual_outcome.isnot(None),
                Prediction.bet_side == Match.actual_outcome,
            )
        )
    ).scalar() or 0

    accuracy = round(correct / total, 4) if total > 0 else 0.0
    min_preds = track_cfg["min_preds"]
    min_acc   = track_cfg["min_accuracy"]

    pred_progress = min(1.0, total / min_preds) if min_preds else 0.0
    acc_progress  = min(1.0, accuracy / min_acc) if min_acc else 0.0
    overall       = round((pred_progress + acc_progress) / 2, 4)

    certified = total >= min_preds and accuracy >= min_acc

    return {
        "user_id":           current_user.id,
        "track":             track,
        "track_name":        track_cfg["name"],
        "certified":         certified,
        "progress":          overall,
        "predictions_done":  total,
        "predictions_needed":max(0, min_preds - total),
        "accuracy":          accuracy,
        "accuracy_needed":   max(0.0, round(min_acc - accuracy, 4)),
    }
