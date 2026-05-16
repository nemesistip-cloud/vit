"""app/modules/compliance/routes.py
Security & Compliance Layer — Phase 5/14
Jurisdictional contracts, tax automation, and responsible gaming.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])

@router.get("/jurisdiction-config")
async def get_config(country: str, current_user: User = Depends(get_current_user)):
    return {"country": country, "user_id": current_user.id, "max_stake": 500, "kyc_required": True, "tax_rate": 0.15}

@router.post("/responsible-gaming/set-limits")
async def set_gaming_limits(daily_limit: float, current_user: User = Depends(get_current_user)):
    return {"status": "limit_set", "user_id": current_user.id, "daily_limit": daily_limit, "cooldown_period": "24h"}
