"""app/modules/data_sovereignty/routes.py
Data Sovereignty Layer — Prediction NFTs (pNFTs), Data DAO, Verifiable Resumes.

Real prediction data is read from the DB. ZK-proof and NFT features are stubs
that explicitly indicate they require a connected ZK/blockchain provider.
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

router = APIRouter(prefix="/api/data-sovereignty", tags=["Data Sovereignty"])


@router.get("/prediction-resume")
async def get_resume(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a verifiable prediction resume for the given user.

    Accuracy and prediction counts are computed live from the Prediction table.
    ZK-proof generation requires an external ZK provider (not yet configured).
    """
    # Only allow self-lookup or admin
    if current_user.id != user_id and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Can only view your own resume")

    from app.db.models import Match

    total_result = await db.execute(
        select(func.count(Prediction.id)).where(Prediction.user_id == user_id)
    )
    total_predictions = total_result.scalar() or 0

    # Count correct: where bet_side matches the match's actual_outcome (settled only)
    from sqlalchemy import join as sqljoin
    correct_result = await db.execute(
        select(func.count(Prediction.id))
        .select_from(
            sqljoin(Prediction, Match, Prediction.match_id == Match.id)
        )
        .where(
            Prediction.user_id == user_id,
            Match.actual_outcome.isnot(None),
            Prediction.bet_side == Match.actual_outcome,
        )
    )
    correct = correct_result.scalar() or 0

    accuracy = round(correct / total_predictions, 4) if total_predictions > 0 else 0.0

    # Latest prediction timestamp
    latest = (
        await db.execute(
            select(Prediction.timestamp)
            .where(Prediction.user_id == user_id)
            .order_by(Prediction.timestamp.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return {
        "user_id":             user_id,
        "requested_by":        current_user.id,
        "total_predictions":   total_predictions,
        "correct_predictions": correct,
        "accuracy_verified":   accuracy,
        "last_prediction_at":  latest.isoformat() if latest else None,
        "zk_proof":            None,
        "zk_note":             (
            "ZK-proof generation requires a connected zero-knowledge provider. "
            "Set ZK_PROVIDER_URL in Secrets to enable."
        ),
    }


@router.post("/pnft/mint")
async def mint_performance_nft(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mint a Performance NFT (pNFT) based on the user's verified prediction record.

    Requires an on-chain minting provider. Currently returns a queued status
    with real accuracy data while the minting backend is pending deployment.
    """
    from app.db.models import Match
    from sqlalchemy import join as sqljoin

    total_result = await db.execute(
        select(func.count(Prediction.id)).where(Prediction.user_id == current_user.id)
    )
    total = total_result.scalar() or 0

    # Count correct: bet_side matches actual_outcome (settled predictions only)
    correct_result = await db.execute(
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
    correct = correct_result.scalar() or 0
    accuracy = round(correct / total, 4) if total > 0 else 0.0
    accuracy_pct = int(accuracy * 100)

    if total < 10:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 10 predictions to mint a pNFT (you have {total})",
        )

    badge_label = (
        "Elite Analyst" if accuracy >= 0.75 else
        "Advanced Analyst" if accuracy >= 0.60 else
        "Analyst"
    )

    return {
        "user_id":    current_user.id,
        "nft_id":     None,
        "status":     "queued",
        "metadata":   f"{accuracy_pct}% Win Rate — {badge_label}",
        "accuracy":   accuracy,
        "total_preds": total,
        "note": (
            "On-chain minting requires a connected Base L2 provider. "
            "Set BLOCKCHAIN_ENABLED=true and BASE_RPC_URL in Secrets to enable."
        ),
    }
