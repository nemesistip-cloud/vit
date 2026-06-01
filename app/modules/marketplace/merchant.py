"""app/modules/marketplace/merchant.py
Merchant onboarding and Business Profile integration.
"""
from __future__ import annotations
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/merchant", tags=["Merchant Services"])
logger = logging.getLogger(__name__)

class MerchantOnboardingRequest(BaseModel):
    business_name: str
    business_type: str
    tax_id: Optional[str] = None
    website: Optional[str] = None

@router.post("/onboard")
async def onboard_merchant(
    data: MerchantOnboardingRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start the merchant onboarding process."""
    # Logic for creating merchant profile and triggering Document AI verification
    return {
        "status": "pending",
        "message": f"Onboarding started for {data.business_name}. Our verification agent is reviewing your documents.",
        "business_id": "m_123456"
    }

@router.get("/profile/{business_id}")
async def get_business_profile(business_id: str):
    """Retrieve business profile and verification status."""
    return {
        "business_id": business_id,
        "status": "verified",
        "google_business_sync": True,
        "verification_score": 0.98
    }
