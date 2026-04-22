"""Oracle system — Module C5.

Receives match results from external oracle sources, requires 2-of-3
agreement before triggering settlement. Disputes are flagged for admin.
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.database import get_db
from app.modules.blockchain.models import OracleResult, ConsensusPrediction, ConsensusStatus
from app.modules.blockchain.settlement import settle_match

router = APIRouter(tags=["Oracle"])
logger = logging.getLogger(__name__)

_MIN_AGREEMENT = 2
_MAX_SOURCES = 3


def _require_oracle_key(x_oracle_key: str = Header(...)):
    expected = os.getenv("ORACLE_API_KEY", "")
    if not expected or x_oracle_key != expected:
        raise HTTPException(403, "Invalid oracle API key")


class OracleResultBody(BaseModel):
    match_id: str
    source: str
    home_score: int
    away_score: int


@router.post("/api/oracle/result")
async def submit_oracle_result(
    body: OracleResultBody,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_oracle_key),
):
    """Internal endpoint — oracle providers submit confirmed match results."""
    outcome = "home" if body.home_score > body.away_score else (
        "draw" if body.home_score == body.away_score else "away"
    )

    existing = await db.execute(
        select(OracleResult).where(
            OracleResult.match_id == body.match_id,
            OracleResult.source == body.source,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Oracle {body.source} already submitted result for {body.match_id}")

    oracle_rec = OracleResult(
        match_id=body.match_id,
        source=body.source,
        home_score=body.home_score,
        away_score=body.away_score,
        result=outcome,
        submitted_at=datetime.utcnow(),
    )
    db.add(oracle_rec)
    await db.flush()

    all_results_res = await db.execute(
        select(OracleResult).where(OracleResult.match_id == body.match_id)
    )
    all_results = all_results_res.scalars().all()

    outcome_counts: dict[str, int] = {}
    for r in all_results:
        outcome_counts[r.result] = outcome_counts.get(r.result, 0) + 1

    agreed_outcome: Optional[str] = None
    for outcome_val, count in outcome_counts.items():
        if count >= _MIN_AGREEMENT:
            agreed_outcome = outcome_val
            break

    response: dict = {"status": "received", "source": body.source, "result": outcome}

    if agreed_outcome:
        for r in all_results:
            r.is_accepted = r.result == agreed_outcome
        await db.flush()

        cp_res = await db.execute(
            select(ConsensusPrediction).where(ConsensusPrediction.match_id == body.match_id)
        )
        cp = cp_res.scalar_one_or_none()
        if cp and cp.status not in (ConsensusStatus.SETTLED.value, ConsensusStatus.VOIDED.value):
            try:
                await settle_match(body.match_id, agreed_outcome, db)
            except Exception as exc:
                logger.error(f"Settlement failed for {body.match_id}: {exc}")

        response["consensus"] = agreed_outcome
        response["status"] = "settled"

    elif len(all_results) >= _MAX_SOURCES:
        for r in all_results:
            r.dispute_flag = True
        logger.warning(f"Dispute flagged for match {body.match_id}: {outcome_counts}")
        response["status"] = "dispute_flagged"

    await db.commit()
    return response


@router.get("/api/admin/oracle/disputes")
async def list_disputes(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: list all disputed oracle results."""
    result = await db.execute(
        select(OracleResult).where(OracleResult.dispute_flag == True)
        .order_by(OracleResult.submitted_at.desc())
    )
    rows = result.scalars().all()
    disputes: dict[str, list] = {}
    for r in rows:
        disputes.setdefault(r.match_id, []).append({
            "source": r.source,
            "home_score": r.home_score,
            "away_score": r.away_score,
            "result": r.result,
            "submitted_at": r.submitted_at.isoformat(),
        })
    return {"disputes": disputes, "total_matches": len(disputes)}


class ResolveDisputeBody(BaseModel):
    result: str


@router.post("/api/admin/oracle/resolve/{match_id}")
async def resolve_dispute(
    match_id: str,
    body: ResolveDisputeBody,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: manually resolve a disputed match result and trigger settlement."""
    if body.result not in ("home", "draw", "away"):
        raise HTTPException(400, "result must be 'home', 'draw', or 'away'")

    result = await db.execute(
        select(OracleResult).where(OracleResult.match_id == match_id)
    )
    records = result.scalars().all()
    if not records:
        raise HTTPException(404, "No oracle results found for this match")

    for r in records:
        r.dispute_flag = False
        r.is_accepted = r.result == body.result

    cp_res = await db.execute(
        select(ConsensusPrediction).where(ConsensusPrediction.match_id == match_id)
    )
    cp = cp_res.scalar_one_or_none()
    if cp and cp.status not in (ConsensusStatus.SETTLED.value, ConsensusStatus.VOIDED.value):
        await settle_match(match_id, body.result, db)

    await db.commit()
    return {"status": "resolved", "match_id": match_id, "result": body.result}
