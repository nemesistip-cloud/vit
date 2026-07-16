"""AI Verification Routes — anchor proofs, verify, dispute."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.ai_verification.models import AttestationKind
from app.modules.ai_verification.service import (
    anchor_inference,
    bootstrap_model_registry,
    get_verification_stats,
    raise_dispute,
    resolve_dispute,
    verify_proof,
)

router = APIRouter(prefix="/api/ai-verify", tags=["ai-verification"])


class AnchorRequest(BaseModel):
    model_id: str
    attestation_kind: AttestationKind
    input_data: Any
    output_data: Any
    confidence: Optional[float] = None
    ref_match_id: Optional[int] = None
    ref_prediction_id: Optional[int] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None


class DisputeRequest(BaseModel):
    proof_hash: str
    reason: str
    challenger_user_id: Optional[int] = None
    evidence_hash: Optional[str] = None


class ResolveDisputeRequest(BaseModel):
    upheld: bool
    resolver_user_id: int
    resolution_notes: Optional[str] = None
    slash_amount: float = 0.0


@router.post("/bootstrap")
async def bootstrap_models(db: AsyncSession = Depends(get_db)):
    count = await bootstrap_model_registry(db)
    return {"created": count, "message": f"Registered {count} AI model attestations"}


@router.get("/stats")
async def verification_stats(db: AsyncSession = Depends(get_db)):
    return await get_verification_stats(db)


@router.get("/attestation-kinds")
async def list_kinds():
    return {"kinds": [k.value for k in AttestationKind]}


@router.post("/anchor")
async def anchor_proof(req: AnchorRequest, db: AsyncSession = Depends(get_db)):
    try:
        proof = await anchor_inference(
            db,
            model_id=req.model_id,
            attestation_kind=req.attestation_kind,
            input_data=req.input_data,
            output_data=req.output_data,
            confidence=req.confidence,
            ref_match_id=req.ref_match_id,
            ref_prediction_id=req.ref_prediction_id,
            input_summary=req.input_summary,
            output_summary=req.output_summary,
        )
        return {
            "proof_hash": proof.proof_hash,
            "input_hash": proof.input_hash,
            "output_hash": proof.output_hash,
            "status": proof.status.value,
            "anchored_at": proof.anchored_at.isoformat() if proof.anchored_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify/{proof_hash}")
async def verify_inference_proof(
    proof_hash: str,
    verifier_user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        proof = await verify_proof(db, proof_hash, verifier_user_id)
        return {
            "proof_hash": proof.proof_hash,
            "status": proof.status.value,
            "verified_at": proof.verified_at.isoformat() if proof.verified_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/disputes")
async def create_dispute(req: DisputeRequest, db: AsyncSession = Depends(get_db)):
    try:
        dispute = await raise_dispute(
            db,
            proof_hash=req.proof_hash,
            reason=req.reason,
            challenger_user_id=req.challenger_user_id,
            evidence_hash=req.evidence_hash,
        )
        return {
            "dispute_id": dispute.id,
            "proof_id": dispute.proof_id,
            "reason": dispute.reason,
            "created_at": dispute.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/disputes/{dispute_id}/resolve")
async def resolve_ai_dispute(
    dispute_id: int,
    req: ResolveDisputeRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        dispute = await resolve_dispute(
            db,
            dispute_id=dispute_id,
            upheld=req.upheld,
            resolver_user_id=req.resolver_user_id,
            resolution_notes=req.resolution_notes,
            slash_amount=Decimal(str(req.slash_amount)),
        )
        return {
            "dispute_id": dispute.id,
            "upheld": dispute.upheld,
            "resolved": dispute.resolved,
            "stake_slashed": float(dispute.stake_slashed),
            "resolved_at": dispute.resolved_at.isoformat() if dispute.resolved_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
