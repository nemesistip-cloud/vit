"""Campus Gigs (Micro-tasks) API routes — v5.6"""
from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user
from app.modules.academy.models import CampusGig
from app.modules.wallet.services import WalletService, Currency

router = APIRouter(prefix="/api/campus/gigs", tags=["Campus Gigs"])
logger = logging.getLogger(__name__)


class GigCreate(BaseModel):
    title: str
    description: str
    gig_type: str = "general"
    budget_vit: float = 0.0
    budget_ngn: float = 0.0
    university: str
    deadline: Optional[datetime] = None


class GigStatusUpdate(BaseModel):
    status: str


@router.get("")
async def list_gigs(
    university: Optional[str] = Query(None),
    status: Optional[str] = Query("open"),
    gig_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uni = university or getattr(current_user, "university", None)
    q = select(CampusGig)
    if uni:
        q = q.where(CampusGig.university == uni)
    if status:
        q = q.where(CampusGig.status == status)
    if gig_type:
        q = q.where(CampusGig.gig_type == gig_type)
    q = q.order_by(desc(CampusGig.created_at)).limit(50)

    result = await db.execute(q)
    gigs = result.scalars().all()
    return [_gig_dict(g) for g in gigs]


@router.post("")
async def create_gig(
    data: GigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.budget_vit > 0:
        wallet_service = WalletService(db)
        wallet = await wallet_service.get_or_create_wallet(current_user.id)
        balance = await wallet_service.get_balance(wallet.id, Currency.VITCoin)
        from decimal import Decimal
        if balance < Decimal(str(data.budget_vit)):
            raise HTTPException(400, "Insufficient VITCoin balance for gig reward")

    gig = CampusGig(
        title=data.title,
        description=data.description,
        gig_type=data.gig_type,
        budget_vit=data.budget_vit,
        budget_ngn=data.budget_ngn,
        university=data.university,
        deadline=data.deadline,
        posted_by=current_user.id,
        status="open",
    )
    db.add(gig)
    await db.commit()
    await db.refresh(gig)
    return {"id": gig.id, "message": "Gig posted successfully"}


@router.get("/{gig_id}")
async def get_gig(
    gig_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gig = await db.get(CampusGig, gig_id)
    if not gig:
        raise HTTPException(404, "Gig not found")
    return _gig_dict(gig)


@router.post("/{gig_id}/apply")
async def apply_for_gig(
    gig_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gig = await db.get(CampusGig, gig_id)
    if not gig:
        raise HTTPException(404, "Gig not found")
    if gig.status != "open":
        raise HTTPException(400, f"Gig is not open (status: {gig.status})")
    if gig.posted_by == current_user.id:
        raise HTTPException(400, "Cannot apply to your own gig")

    gig.assigned_to = current_user.id
    gig.status = "assigned"
    await db.commit()
    return {"message": "Application accepted — you are now assigned to this gig"}


@router.post("/{gig_id}/complete")
async def complete_gig(
    gig_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gig = await db.get(CampusGig, gig_id)
    if not gig:
        raise HTTPException(404, "Gig not found")
    if gig.posted_by != current_user.id:
        raise HTTPException(403, "Only the gig poster can mark it complete")
    if gig.status != "assigned":
        raise HTTPException(400, "Gig must be assigned before it can be completed")

    gig.status = "completed"
    gig.completed_at = datetime.now(timezone.utc)

    if gig.assigned_to and gig.budget_vit > 0:
        try:
            wallet_service = WalletService(db)
            assignee_wallet = await wallet_service.get_or_create_wallet(gig.assigned_to)
            from decimal import Decimal
            await wallet_service.credit(
                wallet_id=assignee_wallet.id,
                user_id=gig.assigned_to,
                currency=Currency.VITCoin,
                amount=Decimal(str(gig.budget_vit)),
                tx_type="gig_reward",
                reference=f"GIG-{gig.id}",
                metadata={"gig_title": gig.title},
            )
        except Exception as e:
            logger.error(f"Failed to pay gig reward: {e}")

    await db.commit()
    return {"message": "Gig marked complete", "reward_paid_vit": gig.budget_vit}


def _gig_dict(g: CampusGig) -> dict:
    return {
        "id": g.id, "title": g.title, "description": g.description,
        "gig_type": g.gig_type, "budget_vit": g.budget_vit,
        "budget_ngn": g.budget_ngn, "university": g.university,
        "status": g.status, "posted_by": g.posted_by,
        "assigned_to": g.assigned_to,
        "deadline": g.deadline.isoformat() if g.deadline else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "completed_at": g.completed_at.isoformat() if g.completed_at else None,
    }
