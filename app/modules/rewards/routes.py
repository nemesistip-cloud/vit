"""User-facing offerwall & reward history endpoints."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.modules.rewards.models import OfferCompletion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rewards", tags=["Rewards"])

# ── Static offer catalog ─────────────────────────────────────────────────────
# In a production integration these would come from an offerwall provider (e.g. Tapjoy / AdGate).
_OFFERS: list[dict] = [
    {
        "id": "survey-basic",
        "title": "Complete a Short Survey",
        "description": "Answer 5 quick questions about your sports interests.",
        "category": "survey",
        "reward_vitcoin": 5.0,
        "difficulty": "easy",
        "estimated_minutes": 3,
        "status": "active",
    },
    {
        "id": "quiz-football-basics",
        "title": "Football Knowledge Quiz",
        "description": "Test your football knowledge with 10 questions.",
        "category": "quiz",
        "reward_vitcoin": 10.0,
        "difficulty": "medium",
        "estimated_minutes": 5,
        "status": "active",
    },
    {
        "id": "profile-complete",
        "title": "Complete Your Profile",
        "description": "Fill in your team preferences and timezone.",
        "category": "onboarding",
        "reward_vitcoin": 15.0,
        "difficulty": "easy",
        "estimated_minutes": 2,
        "status": "active",
    },
    {
        "id": "invite-friend",
        "title": "Invite a Friend",
        "description": "Share your referral code and earn when they join.",
        "category": "referral",
        "reward_vitcoin": 50.0,
        "difficulty": "easy",
        "estimated_minutes": 1,
        "status": "active",
    },
    {
        "id": "first-prediction",
        "title": "Make Your First Prediction",
        "description": "Run a match prediction using the VIT prediction engine.",
        "category": "activity",
        "reward_vitcoin": 20.0,
        "difficulty": "easy",
        "estimated_minutes": 2,
        "status": "active",
    },
    {
        "id": "upload-dataset",
        "title": "Upload a Training Dataset",
        "description": "Submit a CSV or JSON dataset for quality scoring.",
        "category": "activity",
        "reward_vitcoin": 25.0,
        "difficulty": "medium",
        "estimated_minutes": 10,
        "status": "active",
    },
    {
        "id": "daily-login",
        "title": "Daily Login Streak (7 days)",
        "description": "Log in every day for 7 consecutive days.",
        "category": "streak",
        "reward_vitcoin": 35.0,
        "difficulty": "medium",
        "estimated_minutes": 0,
        "status": "active",
    },
    {
        "id": "video-tutorial",
        "title": "Watch the VIT Tutorial Video",
        "description": "Watch the 5-minute VIT platform walkthrough.",
        "category": "education",
        "reward_vitcoin": 8.0,
        "difficulty": "easy",
        "estimated_minutes": 5,
        "status": "active",
    },
]


class OfferOut(BaseModel):
    id: str
    title: str
    description: str
    category: str
    reward_vitcoin: float
    difficulty: str
    estimated_minutes: int
    status: str


class EarnHistoryItem(BaseModel):
    id: int
    provider: str
    reward_type: str
    status: str
    amount: float
    currency: str
    created_at: str


@router.get("/offers", response_model=List[OfferOut])
async def list_offers(current_user=Depends(get_current_user)):
    """Return the active offer catalog with VITCoin reward amounts."""
    return [OfferOut(**o) for o in _OFFERS if o["status"] == "active"]


@router.get("/history", response_model=List[EarnHistoryItem])
async def earn_history(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's completed offer/reward history."""
    result = await db.execute(
        select(OfferCompletion)
        .where(OfferCompletion.user_id == current_user.id)
        .order_by(desc(OfferCompletion.created_at))
        .limit(100)
    )
    records = result.scalars().all()
    return [
        EarnHistoryItem(
            id=r.id,
            provider=r.provider,
            reward_type=r.reward_type,
            status=r.status,
            amount=float(r.amount),
            currency=r.currency,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in records
    ]


@router.get("/summary")
async def rewards_summary(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return total earned VITCoin and completion count for the current user."""
    from sqlalchemy import func as _func
    result = await db.execute(
        select(
            _func.count(OfferCompletion.id).label("count"),
            _func.coalesce(_func.sum(OfferCompletion.amount), 0).label("total"),
        ).where(
            OfferCompletion.user_id == current_user.id,
            OfferCompletion.status == "confirmed",
        )
    )
    row = result.one()
    return {
        "total_earned_vitcoin": float(row.total),
        "completed_offers": int(row.count),
        "available_offers": len([o for o in _OFFERS if o["status"] == "active"]),
    }
