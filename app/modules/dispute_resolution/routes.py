"""app/modules/dispute_resolution/routes.py
Dispute Resolution Layer — Phase 12/39
VIT Court, oracle consensus, and challenge windows.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/court", tags=["Dispute Resolution"])

@router.post("/challenge")
async def challenge_outcome(prediction_id: int, evidence: str, current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "dispute_id": 101, "status": "pending_jurors", "stake_locked": 50.0}

@router.get("/oracle/consensus")
async def get_oracle_data(prediction_id: int, current_user: User = Depends(get_current_user)):
    return {"requested_by": current_user.id, "consensus": "home_win", "sources_queried": 7, "agreement": 1.0}
