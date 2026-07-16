"""Treasury Routes — pool management, deposits, grants, allocations."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_admin, get_current_user
from app.modules.treasury.models import PoolType
from app.modules.treasury.service import (
    allocate_from_pool,
    bootstrap_treasury_pools,
    deposit_to_pool,
    distribute_epoch_rewards,
    execute_grant,
    get_pool_summary,
    get_treasury_overview,
    review_grant,
    submit_grant_proposal,
)

router = APIRouter(prefix="/api/treasury", tags=["treasury"])


class DepositRequest(BaseModel):
    pool_type: PoolType
    amount: float
    source: str
    depositor_user_id: Optional[int] = None
    notes: Optional[str] = None


class AllocateRequest(BaseModel):
    pool_type: PoolType
    amount: float
    reason: str
    recipient_user_id: Optional[int] = None


class GrantProposalRequest(BaseModel):
    title: str
    description: str
    pool_type: PoolType
    requested_amount: float
    proposer_user_id: Optional[int] = None
    milestones: dict = Field(default_factory=dict)
    recipient_user_id: Optional[int] = None


class ReviewGrantRequest(BaseModel):
    approved: bool
    reviewed_by: int
    approved_amount: Optional[float] = None
    review_notes: Optional[str] = None


class EpochRewardRequest(BaseModel):
    total_block_reward: float


# ── READ-ONLY (public) ────────────────────────────────────────────────────────

@router.get("/overview")
async def treasury_overview(db: AsyncSession = Depends(get_db)):
    return await get_treasury_overview(db)


@router.get("/pools")
async def list_pools(db: AsyncSession = Depends(get_db)):
    return {"pools": await get_pool_summary(db)}


@router.get("/grants")
async def list_grants(db: AsyncSession = Depends(get_db)):
    from app.modules.treasury.models import TreasuryGrantProposal
    from sqlalchemy import select
    rows = (await db.execute(select(TreasuryGrantProposal).order_by(
        TreasuryGrantProposal.created_at.desc()).limit(50))).scalars().all()
    return {"proposals": [
        {
            "id": r.id, "title": r.title, "status": r.status.value,
            "pool_type": r.pool_type.value,
            "requested_amount": float(r.requested_amount),
            "approved_amount": float(r.approved_amount) if r.approved_amount else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]}


# ── WRITE — admin only ────────────────────────────────────────────────────────

@router.post("/bootstrap", summary="Admin: bootstrap treasury pools")
async def bootstrap_pools(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    count = await bootstrap_treasury_pools(db)
    return {"created": count, "message": f"Bootstrapped {count} treasury pools"}


@router.post("/deposit", summary="Admin: deposit to treasury pool")
async def deposit(
    req: DepositRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    try:
        pool = await deposit_to_pool(
            db,
            pool_type=req.pool_type,
            amount=Decimal(str(req.amount)),
            source=req.source,
            depositor_user_id=req.depositor_user_id,
            notes=req.notes,
        )
        return {
            "pool_type": pool.pool_type.value,
            "new_balance": float(pool.balance),
            "total_deposited": float(pool.total_deposited),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/allocate", summary="Admin: allocate funds from treasury pool")
async def allocate(
    req: AllocateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    try:
        alloc = await allocate_from_pool(
            db,
            pool_type=req.pool_type,
            amount=Decimal(str(req.amount)),
            reason=req.reason,
            recipient_user_id=req.recipient_user_id,
        )
        return {
            "allocation_id": alloc.id,
            "amount": float(alloc.amount),
            "tx_hash": alloc.tx_hash,
            "status": alloc.status.value,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/distribute-epoch", summary="Admin: distribute epoch rewards")
async def distribute_epoch(
    req: EpochRewardRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    distributed = await distribute_epoch_rewards(db, Decimal(str(req.total_block_reward)))
    return {"distributed": {k: float(v) for k, v in distributed.items()}}


# ── GRANTS — submit (auth user) / review + execute (admin) ───────────────────

@router.post("/grants", summary="Submit a grant proposal")
async def submit_grant(
    req: GrantProposalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proposal = await submit_grant_proposal(
        db,
        title=req.title,
        description=req.description,
        pool_type=req.pool_type,
        requested_amount=Decimal(str(req.requested_amount)),
        proposer_user_id=current_user.id,
        milestones=req.milestones,
        recipient_user_id=req.recipient_user_id or current_user.id,
    )
    return {
        "proposal_id": proposal.id,
        "title": proposal.title,
        "status": proposal.status.value,
        "requested_amount": float(proposal.requested_amount),
        "created_at": proposal.created_at.isoformat(),
    }


@router.post("/grants/{proposal_id}/review", summary="Admin: review grant proposal")
async def review_grant_proposal(
    proposal_id: int,
    req: ReviewGrantRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        proposal = await review_grant(
            db,
            proposal_id=proposal_id,
            approved=req.approved,
            reviewed_by=admin.id,
            approved_amount=Decimal(str(req.approved_amount)) if req.approved_amount else None,
            review_notes=req.review_notes,
        )
        return {
            "proposal_id": proposal.id,
            "status": proposal.status.value,
            "approved_amount": float(proposal.approved_amount) if proposal.approved_amount else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/grants/{proposal_id}/execute", summary="Admin: execute approved grant")
async def execute_grant_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    try:
        alloc = await execute_grant(db, proposal_id)
        return {
            "allocation_id": alloc.id,
            "amount": float(alloc.amount),
            "tx_hash": alloc.tx_hash,
            "released_at": alloc.released_at.isoformat() if alloc.released_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
