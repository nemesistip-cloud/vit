# app/modules/governance/service.py
"""Governance service — proposals, voting, execution, config management."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.governance.models import GovernanceConfig, Proposal, Vote

logger = logging.getLogger(__name__)

DEFAULT_VOTING_PERIOD_DAYS = 7
DEFAULT_TIMELOCK_SECONDS   = 86_400     # 24 h
DEFAULT_QUORUM             = 1_000.0    # voting-power units


# ── Config seed ───────────────────────────────────────────────────────────────

async def seed_default_config(db: AsyncSession) -> None:
    existing = (await db.execute(select(func.count(GovernanceConfig.id)))).scalar() or 0
    if existing > 0:
        return
    defaults = [
        ("protocol_fee_pct",       "0.15",   "float",  "Protocol fee percentage on marketplace calls"),
        ("validator_reward_share", "0.40",   "float",  "Fraction of pool fees distributed to validators"),
        ("burn_rate",              "0.20",   "float",  "Fraction of settlement fees burned"),
        ("min_stake_vitcoin",      "100",    "int",    "Minimum VITCoin stake to become a validator"),
        ("voting_period_days",     "7",      "int",    "Default governance voting period in days"),
        ("timelock_seconds",       "86400",  "int",    "Seconds between proposal passing and execution"),
        ("quorum_required",        "1000",   "float",  "Minimum total voting power for a proposal to pass"),
        ("max_proposals_per_user", "5",      "int",    "Max open proposals per user at a time"),
    ]
    for key, value, dtype, desc in defaults:
        db.add(GovernanceConfig(key=key, value=value, data_type=dtype, description=desc))
    await db.commit()
    logger.info("Governance: seeded 8 default config entries")


async def get_config(db: AsyncSession, key: str) -> Optional[GovernanceConfig]:
    result = await db.execute(
        select(GovernanceConfig).where(GovernanceConfig.key == key)
    )
    return result.scalar_one_or_none()


async def list_configs(db: AsyncSession) -> list[GovernanceConfig]:
    result = await db.execute(select(GovernanceConfig).order_by(GovernanceConfig.key))
    return list(result.scalars().all())


async def update_config(
    db: AsyncSession, key: str, value: str, updated_by: int
) -> GovernanceConfig:
    cfg = await get_config(db, key)
    if not cfg:
        raise ValueError(f"Config key '{key}' not found")
    cfg.value      = value
    cfg.updated_by = updated_by
    await db.commit()
    await db.refresh(cfg)
    return cfg


# ── Voting-power calculation ──────────────────────────────────────────────────

async def _calc_voting_power(db: AsyncSession, user_id: int) -> float:
    """
    voting_power = vitcoin_staked × trust_score_normalised
    Falls back gracefully if modules aren't loaded.
    """
    try:
        from app.modules.wallet.services import WalletService
        ws = WalletService(db)
        wallet = await ws.get_or_create_wallet(user_id)
        stake = float(wallet.vitcoin_balance)
    except Exception:
        stake = 0.0

    trust_score = 1.0
    try:
        from app.modules.trust.engine import get_user_trust_score
        ts = await get_user_trust_score(db, user_id)
        trust_score = max(0.1, min(ts / 100.0, 2.0))
    except Exception:
        pass

    return max(1.0, round(stake * trust_score, 4))


# ── Proposal CRUD ─────────────────────────────────────────────────────────────

async def create_proposal(
    db: AsyncSession,
    proposer_id: int,
    title: str,
    description: str,
    category: str = "general",
    change_payload: Optional[dict] = None,
    voting_period_days: int = DEFAULT_VOTING_PERIOD_DAYS,
) -> Proposal:
    # Limit open proposals per user
    # Read per-user proposal limit from DB config (falls back to 5)
    max_proposals_cfg = await get_config(db, "max_proposals_per_user")
    try:
        max_proposals = int(max_proposals_cfg.value) if max_proposals_cfg else 5
    except (TypeError, ValueError):
        max_proposals = 5

    open_count = (await db.execute(
        select(func.count(Proposal.id)).where(
            Proposal.proposer_id == proposer_id,
            Proposal.status.in_(["draft", "active"]),
        )
    )).scalar() or 0
    if open_count >= max_proposals:
        raise ValueError(
            f"You already have {open_count} open proposals (limit: {max_proposals}). "
            "Close or execute existing ones first."
        )

    # Load timelock and quorum from live DB config, falling back to module defaults
    timelock_cfg = await get_config(db, "timelock_seconds")
    try:
        resolved_timelock = int(timelock_cfg.value) if timelock_cfg else DEFAULT_TIMELOCK_SECONDS
    except (TypeError, ValueError):
        resolved_timelock = DEFAULT_TIMELOCK_SECONDS

    quorum_cfg = await get_config(db, "quorum_required")
    try:
        resolved_quorum = float(quorum_cfg.value) if quorum_cfg else DEFAULT_QUORUM
    except (TypeError, ValueError):
        resolved_quorum = DEFAULT_QUORUM

    now = datetime.now(timezone.utc)
    proposal = Proposal(
        proposer_id=proposer_id,
        title=title,
        description=description,
        category=category,
        change_payload=json.dumps(change_payload) if change_payload else None,
        status="active",
        voting_starts_at=now,
        voting_ends_at=now + timedelta(days=voting_period_days),
        timelock_seconds=resolved_timelock,
        quorum_required=resolved_quorum,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    logger.info(f"Governance: proposal '{title}' created by user {proposer_id}")
    return proposal


async def get_proposal(db: AsyncSession, proposal_id: int) -> Optional[Proposal]:
    result = await db.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    return result.scalar_one_or_none()


async def list_proposals(
    db: AsyncSession,
    status: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Proposal], int]:
    q = select(Proposal)
    if status:
        q = q.where(Proposal.status == status)
    if category:
        q = q.where(Proposal.category == category)

    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar() or 0

    q = q.order_by(Proposal.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all()), total


# ── Voting ────────────────────────────────────────────────────────────────────

async def cast_vote(
    db: AsyncSession,
    proposal_id: int,
    voter_id: int,
    choice: str,
    reason: Optional[str] = None,
) -> Vote:
    if choice not in ("for", "against", "abstain"):
        raise ValueError("Choice must be 'for', 'against', or 'abstain'")

    proposal = await get_proposal(db, proposal_id)
    if not proposal:
        raise ValueError("Proposal not found")
    if proposal.status != "active":
        raise ValueError(f"Proposal is not active (current status: {proposal.status})")

    now = datetime.now(timezone.utc)
    ends = proposal.voting_ends_at
    if ends and ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)
    if ends and now > ends:
        raise ValueError("Voting period has ended for this proposal")

    # Check for existing vote
    existing = (await db.execute(
        select(Vote).where(Vote.proposal_id == proposal_id, Vote.voter_id == voter_id)
    )).scalar_one_or_none()
    if existing:
        raise ValueError("You have already voted on this proposal")

    power = await _calc_voting_power(db, voter_id)

    vote = Vote(
        proposal_id=proposal_id,
        voter_id=voter_id,
        choice=choice,
        voting_power=power,
        reason=reason,
    )
    db.add(vote)

    # Update cached tallies
    if choice == "for":
        proposal.votes_for      = (proposal.votes_for or 0.0) + power
    elif choice == "against":
        proposal.votes_against  = (proposal.votes_against or 0.0) + power
    else:
        proposal.votes_abstain  = (proposal.votes_abstain or 0.0) + power

    await db.commit()
    await db.refresh(vote)

    # Check if quorum reached and voting ended
    await _auto_close_if_needed(db, proposal)
    return vote


async def _auto_close_if_needed(db: AsyncSession, proposal: Proposal) -> None:
    now = datetime.now(timezone.utc)
    ends = proposal.voting_ends_at
    if ends and ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)
    if ends and now < ends:
        return   # still open

    total = proposal.total_votes
    if total < proposal.quorum_required:
        proposal.status = "rejected"
        logger.info(f"Proposal {proposal.id}: rejected (quorum not met: {total:.1f} < {proposal.quorum_required})")
    elif proposal.votes_for > proposal.votes_against:
        proposal.status = "passed"
        logger.info(f"Proposal {proposal.id}: passed ({proposal.votes_for:.1f} for, {proposal.votes_against:.1f} against)")
    else:
        proposal.status = "rejected"
        logger.info(f"Proposal {proposal.id}: rejected by vote")

    await db.commit()


# ── Execution ─────────────────────────────────────────────────────────────────

async def execute_proposal(
    db: AsyncSession,
    proposal_id: int,
    executor_id: int,
) -> Proposal:
    proposal = await get_proposal(db, proposal_id)
    if not proposal:
        raise ValueError("Proposal not found")
    if proposal.status != "passed":
        raise ValueError(f"Can only execute passed proposals (current: {proposal.status})")

    now = datetime.now(timezone.utc)
    passed_at = proposal.updated_at or proposal.created_at
    if passed_at and passed_at.tzinfo is None:
        passed_at = passed_at.replace(tzinfo=timezone.utc)
    if passed_at and (now - passed_at).total_seconds() < proposal.timelock_seconds:
        remaining = proposal.timelock_seconds - int((now - passed_at).total_seconds())
        raise ValueError(f"Timelock active. Execute in {remaining}s.")

    # Apply change_payload to GovernanceConfig if present
    note = "Executed with no parameter changes."
    if proposal.change_payload:
        try:
            payload = json.loads(proposal.change_payload)
            changed = []
            for key, value in payload.items():
                cfg = await get_config(db, key)
                if cfg:
                    cfg.value      = str(value)
                    cfg.updated_by = executor_id
                    changed.append(f"{key}={value}")
            note = f"Config updated: {', '.join(changed)}" if changed else "No matching config keys found."
        except Exception as e:
            note = f"Payload parse error: {e}"

    proposal.status        = "executed"
    proposal.executed_at   = now
    proposal.execution_note = note

    await db.commit()
    await db.refresh(proposal)
    logger.info(f"Governance: proposal {proposal_id} executed by user {executor_id}: {note}")
    return proposal


# ── Tally refresh (call periodically or on-demand) ────────────────────────────

async def refresh_proposal_statuses(db: AsyncSession) -> int:
    """Close expired active proposals and return count updated."""
    result = await db.execute(
        select(Proposal).where(Proposal.status == "active")
    )
    proposals = result.scalars().all()
    updated = 0
    for p in proposals:
        before = p.status
        await _auto_close_if_needed(db, p)
        if p.status != before:
            updated += 1
    return updated
