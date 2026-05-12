"""Treasury Service — pool management, grant lifecycle, governance-controlled spending."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.treasury.models import (
    AllocationStatus,
    GrantProposal,
    PoolType,
    ProposalStatus,
    TreasuryAllocation,
    TreasuryDeposit,
    TreasuryPool,
)

logger = logging.getLogger(__name__)

INITIAL_POOLS: dict[PoolType, dict] = {
    PoolType.VALIDATOR_REWARDS:   {"allocation_pct": Decimal("30"), "auto_refill": True},
    PoolType.AI_INFRASTRUCTURE:   {"allocation_pct": Decimal("20"), "auto_refill": False},
    PoolType.ECOSYSTEM_GRANTS:    {"allocation_pct": Decimal("15"), "auto_refill": False},
    PoolType.RESERVE:             {"allocation_pct": Decimal("20"), "auto_refill": False},
    PoolType.ORACLE_INCENTIVES:   {"allocation_pct": Decimal("10"), "auto_refill": True},
    PoolType.PREDICTION_LIQUIDITY:{"allocation_pct": Decimal("3"),  "auto_refill": False},
    PoolType.BUG_BOUNTY:          {"allocation_pct": Decimal("1"),  "auto_refill": False},
    PoolType.TEAM_VESTING:        {"allocation_pct": Decimal("1"),  "auto_refill": False},
}


async def bootstrap_treasury_pools(db: AsyncSession) -> int:
    """Create pool rows if they don't exist. Returns count created."""
    created = 0
    for pool_type, cfg in INITIAL_POOLS.items():
        existing = await db.scalar(
            select(TreasuryPool).where(TreasuryPool.pool_type == pool_type)
        )
        if not existing:
            pool = TreasuryPool(
                pool_type=pool_type,
                balance=Decimal("0"),
                allocation_pct=cfg["allocation_pct"],
                auto_refill=cfg["auto_refill"],
                description=f"VIT {pool_type.value.replace('_', ' ').title()} pool",
            )
            db.add(pool)
            created += 1
    if created:
        await db.commit()
    return created


async def deposit_to_pool(
    db: AsyncSession,
    pool_type: PoolType,
    amount: Decimal,
    source: str,
    depositor_user_id: int | None = None,
    notes: str | None = None,
) -> TreasuryPool:
    pool = await db.scalar(select(TreasuryPool).where(TreasuryPool.pool_type == pool_type))
    if not pool:
        raise ValueError(f"Pool {pool_type} not found")

    tx_hash = "0x" + hashlib.sha3_256(
        f"{pool_type}:{amount}:{secrets.token_hex(8)}".encode()
    ).hexdigest()

    pool.balance += amount
    pool.total_deposited += amount

    deposit = TreasuryDeposit(
        pool_type=pool_type,
        amount=amount,
        source=source,
        depositor_user_id=depositor_user_id,
        tx_hash=tx_hash,
        notes=notes,
    )
    db.add(deposit)
    await db.commit()
    await db.refresh(pool)
    return pool


async def distribute_epoch_rewards(
    db: AsyncSession,
    total_block_reward: Decimal,
) -> dict[str, Decimal]:
    """Distribute a block reward epoch across pools by allocation_pct."""
    pools_q = await db.execute(select(TreasuryPool))
    pools = list(pools_q.scalars().all())
    total_pct = sum(p.allocation_pct for p in pools) or Decimal("100")
    distributed: dict[str, Decimal] = {}

    for pool in pools:
        share = (pool.allocation_pct / total_pct) * total_block_reward
        pool.balance += share
        pool.total_deposited += share
        distributed[pool.pool_type.value] = share

    await db.commit()
    return distributed


async def allocate_from_pool(
    db: AsyncSession,
    pool_type: PoolType,
    amount: Decimal,
    reason: str,
    recipient_user_id: int | None = None,
    grant_id: int | None = None,
) -> TreasuryAllocation:
    pool = await db.scalar(select(TreasuryPool).where(TreasuryPool.pool_type == pool_type))
    if not pool:
        raise ValueError(f"Pool {pool_type} not found")
    if pool.balance < amount:
        raise ValueError(f"Insufficient pool balance: {pool.balance} < {amount}")

    pool.balance -= amount
    pool.total_spent += amount

    tx_hash = "0x" + hashlib.sha3_256(
        f"{pool_type}:{recipient_user_id}:{amount}:{secrets.token_hex(8)}".encode()
    ).hexdigest()

    alloc = TreasuryAllocation(
        pool_id=pool.id,
        grant_id=grant_id,
        recipient_user_id=recipient_user_id,
        amount=amount,
        reason=reason,
        status=AllocationStatus.RELEASED,
        tx_hash=tx_hash,
        released_at=datetime.now(timezone.utc),
    )
    db.add(alloc)
    await db.commit()
    await db.refresh(alloc)
    return alloc


async def get_pool_summary(db: AsyncSession) -> list[dict]:
    pools_q = await db.execute(select(TreasuryPool))
    pools = list(pools_q.scalars().all())
    total_balance = sum(p.balance for p in pools)
    return [
        {
            "pool_type": p.pool_type.value,
            "balance": float(p.balance),
            "total_deposited": float(p.total_deposited),
            "total_spent": float(p.total_spent),
            "allocation_pct": float(p.allocation_pct),
            "share_of_treasury": float(p.balance / total_balance * 100) if total_balance else 0,
            "utilization_pct": float(p.total_spent / p.total_deposited * 100)
            if p.total_deposited else 0,
            "auto_refill": p.auto_refill,
        }
        for p in pools
    ]


async def submit_grant_proposal(
    db: AsyncSession,
    title: str,
    description: str,
    pool_type: PoolType,
    requested_amount: Decimal,
    proposer_user_id: int | None = None,
    milestones: dict | None = None,
    recipient_user_id: int | None = None,
) -> GrantProposal:
    proposal = GrantProposal(
        title=title,
        description=description,
        proposer_user_id=proposer_user_id,
        pool_type=pool_type,
        requested_amount=requested_amount,
        recipient_user_id=recipient_user_id,
        milestones=milestones or {},
        status=ProposalStatus.PENDING,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return proposal


async def review_grant(
    db: AsyncSession,
    proposal_id: int,
    approved: bool,
    reviewed_by: int,
    approved_amount: Decimal | None = None,
    review_notes: str | None = None,
) -> GrantProposal:
    proposal = await db.get(GrantProposal, proposal_id)
    if not proposal:
        raise ValueError("Proposal not found")

    if approved:
        proposal.status = ProposalStatus.APPROVED
        proposal.approved_amount = approved_amount or proposal.requested_amount
        proposal.approved_at = datetime.now(timezone.utc)
    else:
        proposal.status = ProposalStatus.REJECTED

    proposal.reviewed_by = reviewed_by
    proposal.review_notes = review_notes
    await db.commit()
    await db.refresh(proposal)
    return proposal


async def execute_grant(db: AsyncSession, proposal_id: int) -> TreasuryAllocation:
    proposal = await db.get(GrantProposal, proposal_id)
    if not proposal:
        raise ValueError("Proposal not found")
    if proposal.status != ProposalStatus.APPROVED:
        raise ValueError("Proposal not approved")
    if not proposal.approved_amount:
        raise ValueError("No approved amount set")

    alloc = await allocate_from_pool(
        db,
        pool_type=proposal.pool_type,
        amount=proposal.approved_amount,
        reason=f"Grant: {proposal.title}",
        recipient_user_id=proposal.recipient_user_id,
        grant_id=proposal.id,
    )
    proposal.status = ProposalStatus.EXECUTED
    proposal.executed_at = datetime.now(timezone.utc)
    await db.commit()
    return alloc


async def get_treasury_overview(db: AsyncSession) -> dict:
    pools = await get_pool_summary(db)
    total = sum(p["balance"] for p in pools)
    total_spent = sum(p["total_spent"] for p in pools)
    total_deposited = sum(p["total_deposited"] for p in pools)

    pending_grants_q = await db.execute(
        select(func.count(GrantProposal.id)).where(
            GrantProposal.status == ProposalStatus.PENDING
        )
    )
    pending_grants = pending_grants_q.scalar() or 0

    return {
        "total_balance_vit": total,
        "total_deposited_vit": total_deposited,
        "total_spent_vit": total_spent,
        "utilization_pct": (total_spent / total_deposited * 100) if total_deposited else 0,
        "pending_grant_proposals": pending_grants,
        "pools": pools,
    }
