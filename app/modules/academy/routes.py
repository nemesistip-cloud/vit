"""app/modules/academy/routes.py
Academy Layer — Phase 11/38
Certification, bootcamps, and guild incubator.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/academy", tags=["Academy"])

@router.post("/enroll")
async def enroll_academy(track: str, current_user: User = Depends(get_current_user)):
    return {"status": "enrolled", "user_id": current_user.id, "track": track, "next_step": "Validator Bootcamp Module 1"}

@router.get("/certification/status")
async def get_cert_status(current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "certified": False, "progress": 0.45, "track": "VIT Certified Prediction Analyst"}
