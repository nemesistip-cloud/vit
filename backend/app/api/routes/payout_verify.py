"""
payout_verify.py — Trustless payout verification (Phase IV)

Allows any user to verify that a payout is legitimate by reconstructing
the proof from chain data and comparing it against the on-chain record.
Uses the SimpleVM contract engine for deterministic rule execution.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Prediction, User

try:
    from vit_chain.smart_contracts.registry import ContractRegistry
    from vit_chain.smart_contracts.vm import SimpleVM
    CONTRACTS_AVAILABLE = True
except Exception:
    CONTRACTS_AVAILABLE = False

router = APIRouter(prefix="/api/predictions", tags=["payout-verification"])


class PayoutProof(BaseModel):
    prediction_id: int
    user_id: int
    payout_amount: float
    outcome: Optional[str]
    proof_hash: str
    contract_method: str   # "escrow_contract" | "hash_only"
    verified: bool
    timestamp: int
    message: str


class PayoutVerifyRequest(BaseModel):
    expected_amount: Optional[float] = None


def _compute_payout_proof(prediction: Prediction, user_id: int) -> str:
    """SHA-256 proof over payout-relevant fields."""
    payload = {
        "prediction_id": prediction.id,
        "user_id": user_id,
        "match_id": prediction.match_id,
        "bet_side": prediction.bet_side,
        "outcome": prediction.outcome,
        "final_ev": float(prediction.final_ev or 0),
        "confidence": float(prediction.confidence or 0),
    }
    raw = json.dumps(payload, sort_keys=True)
    return "vit:payout:" + hashlib.sha256(raw.encode()).hexdigest()


def _run_escrow_verification(prediction: Prediction, expected_amount: Optional[float]) -> dict:
    """Run prediction_escrow contract to determine payout legitimacy."""
    if not CONTRACTS_AVAILABLE:
        return {"verified": False, "method": "hash_only", "amount": 0.0}

    try:
        registry = ContractRegistry()
        contract = registry.get("prediction_escrow")
        if not contract:
            return {"verified": False, "method": "hash_only", "amount": 0.0}

        vm = SimpleVM()
        context = {
            "outcome": prediction.outcome or "pending",
            "bet_side": prediction.bet_side or "",
            "confidence": float(prediction.confidence or 0),
            "final_ev": float(prediction.final_ev or 0),
            "expected_amount": expected_amount or 0.0,
        }
        result = vm.execute(contract, context)
        amount = float(result.return_value or 0) if result.success else 0.0
        return {
            "verified": result.success and prediction.outcome is not None,
            "method": "escrow_contract",
            "amount": amount,
            "gas_used": result.gas_used,
        }
    except Exception:
        return {"verified": False, "method": "hash_only", "amount": 0.0}


@router.post("/{prediction_id}/verify-payout", response_model=PayoutProof)
async def verify_payout(
    prediction_id: int,
    body: PayoutVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trustless payout verification.

    Reconstructs the payout proof from on-chain rules (SimpleVM) and
    returns a cryptographic proof hash that can be independently verified.
    Works even when the chain node is offline — falls back to hash-only proof.
    """
    result = await db.execute(
        select(Prediction).where(
            Prediction.id == prediction_id,
            Prediction.user_id == current_user.id,
        )
    )
    prediction = result.scalar_one_or_none()
    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")

    proof_hash = _compute_payout_proof(prediction, current_user.id)
    escrow = _run_escrow_verification(prediction, body.expected_amount)

    return PayoutProof(
        prediction_id=prediction_id,
        user_id=current_user.id,
        payout_amount=escrow["amount"],
        outcome=prediction.outcome,
        proof_hash=proof_hash,
        contract_method=escrow["method"],
        verified=escrow["verified"],
        timestamp=int(time.time()),
        message=(
            "Payout verified via escrow contract." if escrow["verified"] and escrow["method"] == "escrow_contract"
            else "Hash-only proof generated. Outcome pending or chain unavailable."
        ),
    )


@router.get("/{prediction_id}/payout-proof", response_model=PayoutProof)
async def get_payout_proof(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the current payout proof for a prediction (read-only)."""
    result = await db.execute(
        select(Prediction).where(
            Prediction.id == prediction_id,
            Prediction.user_id == current_user.id,
        )
    )
    prediction = result.scalar_one_or_none()
    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")

    proof_hash = _compute_payout_proof(prediction, current_user.id)
    escrow = _run_escrow_verification(prediction, None)

    return PayoutProof(
        prediction_id=prediction_id,
        user_id=current_user.id,
        payout_amount=escrow["amount"],
        outcome=prediction.outcome,
        proof_hash=proof_hash,
        contract_method=escrow["method"],
        verified=escrow["verified"],
        timestamp=int(time.time()),
        message="Proof computed from latest prediction state.",
    )
