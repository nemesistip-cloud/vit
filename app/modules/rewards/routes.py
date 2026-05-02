"""User-facing offerwall & reward history endpoints."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.modules.rewards.models import OfferCompletion
from app.modules.wallet.services import WalletService

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


# ── Offer completion (user-facing, no external postback) ─────────────────────

def _offer_payload_hash(user_id: int, offer_id: str, window: str) -> str:
    """
    Deterministic hash used as the idempotency key for internal offer completions.

    `window` is a date string (YYYY-MM-DD) for daily/streak offers, or "once"
    for one-time offers — this lets the same user re-earn daily offers on
    different calendar days while still preventing double-claims on the same day.
    """
    raw = f"internal:{user_id}:{offer_id}:{window}"
    return hashlib.sha256(raw.encode()).hexdigest()


_ONE_TIME_CATEGORIES = {"onboarding", "activity", "referral", "education"}
_DAILY_CATEGORIES    = {"streak", "survey", "quiz"}


@router.post("/complete/{offer_id}")
async def complete_offer(
    offer_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an internal offer as completed and credit VITCoin to the user's wallet.

    Idempotency rules:
    - One-time categories (onboarding, activity, referral, education):
      one completion per user ever.
    - Daily / repeatable categories (streak, survey, quiz):
      one completion per calendar day (UTC).
    """
    offer = next((o for o in _OFFERS if o["id"] == offer_id and o["status"] == "active"), None)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found or not active.")

    category = offer["category"]
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if category in _ONE_TIME_CATEGORIES:
        window = "once"
    else:
        window = today_utc

    payload_hash = _offer_payload_hash(current_user.id, offer_id, window)

    existing = await db.execute(
        select(OfferCompletion).where(
            and_(
                OfferCompletion.user_id == current_user.id,
                OfferCompletion.provider == "internal",
                OfferCompletion.provider_payload_hash == payload_hash,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=(
                "Offer already completed for today."
                if window != "once"
                else "You have already completed this offer."
            ),
        )

    amount = Decimal(str(offer["reward_vitcoin"]))

    now = datetime.now(timezone.utc)
    completion = OfferCompletion(
        user_id=current_user.id,
        provider="internal",
        reward_type=category,
        provider_offer_id=offer_id,
        provider_event_id=f"{offer_id}:{current_user.id}:{window}",
        status="pending",
        amount=amount,
        currency="VITCoin",
        reward_margin=0.0,
        provider_payload={"offer_id": offer_id, "window": window},
        provider_payload_hash=payload_hash,
        provider_signature=None,
        event_metadata={"source": "user_claim", "offer_title": offer["title"]},
        updated_at=now,
    )
    db.add(completion)
    await db.flush()

    try:
        wallet = WalletService(db)
        tx = await wallet.deposit_vitcoin(
            user_id=current_user.id,
            amount=amount,
            description=f"Offer reward: {offer['title']}",
            tx_type="reward",
            metadata={
                "offer_completion_id": completion.id,
                "offer_id": offer_id,
                "provider": "internal",
            },
        )
        completion.wallet_tx_id = str(tx.id) if tx else None
        completion.status = "confirmed"
        logger.info(
            "[rewards] User %d completed offer '%s' → +%s VITCoin",
            current_user.id, offer_id, amount,
        )
    except Exception as exc:
        completion.status = "failed"
        completion.event_metadata["credit_error"] = str(exc)
        await db.commit()
        logger.error("[rewards] Wallet credit failed for offer '%s': %s", offer_id, exc)
        raise HTTPException(status_code=500, detail="Wallet credit failed — please try again.")

    await db.commit()
    await db.refresh(completion)

    return {
        "offer_id": offer_id,
        "offer_title": offer["title"],
        "vitcoin_earned": float(amount),
        "status": completion.status,
        "completion_id": completion.id,
        "message": f"Congratulations! You earned {float(amount):.1f} VITCoin.",
    }
