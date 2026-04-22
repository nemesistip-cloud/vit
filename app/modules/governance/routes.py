# app/modules/governance/routes.py
"""Governance Layer REST API — Module M."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.governance import service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/governance", tags=["governance"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class ProposalCreate(BaseModel):
    title:               str            = Field(..., min_length=5, max_length=256)
    description:         str            = Field(..., min_length=20)
    category:            str            = Field(default="general")
    change_payload:      Optional[dict] = None
    voting_period_days:  int            = Field(default=7, ge=1, le=30)


class CastVote(BaseModel):
    choice: str           = Field(..., pattern="^(for|against|abstain)$")
    reason: Optional[str] = Field(None, max_length=1000)


class ConfigUpdate(BaseModel):
    value: str


def _fmt_proposal(p) -> dict:
    return {
        "id":               p.id,
        "proposer_id":      p.proposer_id,
        "title":            p.title,
        "description":      p.description,
        "category":         p.category,
        "change_payload":   p.change_payload,
        "status":           p.status,
        "voting_starts_at": p.voting_starts_at.isoformat() if p.voting_starts_at else None,
        "voting_ends_at":   p.voting_ends_at.isoformat()   if p.voting_ends_at   else None,
        "timelock_seconds": p.timelock_seconds,
        "executed_at":      p.executed_at.isoformat()      if p.executed_at      else None,
        "execution_note":   p.execution_note,
        "votes_for":        p.votes_for,
        "votes_against":    p.votes_against,
        "votes_abstain":    p.votes_abstain,
        "total_votes":      p.total_votes,
        "approval_pct":     p.approval_pct,
        "quorum_required":  p.quorum_required,
        "created_at":       p.created_at.isoformat() if p.created_at else None,
    }


def _fmt_vote(v) -> dict:
    return {
        "id":           v.id,
        "proposal_id":  v.proposal_id,
        "voter_id":     v.voter_id,
        "choice":       v.choice,
        "voting_power": v.voting_power,
        "reason":       v.reason,
        "voted_at":     v.voted_at.isoformat() if v.voted_at else None,
    }


def _fmt_config(c) -> dict:
    return {
        "key":         c.key,
        "value":       c.value,
        "data_type":   c.data_type,
        "description": c.description,
        "updated_at":  c.updated_at.isoformat() if c.updated_at else None,
    }


# ── Proposals ─────────────────────────────────────────────────────────────────

@router.get("/proposals", summary="List governance proposals")
async def list_proposals(
    status:    Optional[str] = Query(None, enum=["draft", "active", "passed", "rejected", "cancelled", "executed"]),
    category:  Optional[str] = None,
    page:      int           = Query(default=1, ge=1),
    page_size: int           = Query(default=20, ge=1, le=100),
    db:        AsyncSession  = Depends(get_db),
    _:         User          = Depends(get_current_user),
):
    proposals, total = await svc.list_proposals(db, status=status, category=category, page=page, page_size=page_size)
    return {
        "items":     [_fmt_proposal(p) for p in proposals],
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     (total + page_size - 1) // page_size if page_size else 1,
    }


@router.post("/proposals", summary="Create a new proposal", status_code=201)
async def create_proposal(
    body:         ProposalCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    try:
        proposal = await svc.create_proposal(
            db,
            proposer_id=current_user.id,
            title=body.title,
            description=body.description,
            category=body.category,
            change_payload=body.change_payload,
            voting_period_days=body.voting_period_days,
        )
        return _fmt_proposal(proposal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/proposals/{proposal_id}", summary="Get proposal details")
async def get_proposal(
    proposal_id: int,
    db:          AsyncSession = Depends(get_db),
    _:           User         = Depends(get_current_user),
):
    proposal = await svc.get_proposal(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _fmt_proposal(proposal)


# ── Voting ────────────────────────────────────────────────────────────────────

@router.post("/proposals/{proposal_id}/vote", summary="Cast a vote on a proposal")
async def cast_vote(
    proposal_id:  int,
    body:         CastVote,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    try:
        vote = await svc.cast_vote(
            db,
            proposal_id=proposal_id,
            voter_id=current_user.id,
            choice=body.choice,
            reason=body.reason,
        )
        return _fmt_vote(vote)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/proposals/{proposal_id}/votes", summary="List votes for a proposal")
async def list_votes(
    proposal_id: int,
    db:          AsyncSession = Depends(get_db),
    _:           User         = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.modules.governance.models import Vote
    result = await db.execute(
        select(Vote)
        .where(Vote.proposal_id == proposal_id)
        .order_by(Vote.voting_power.desc())
    )
    votes = result.scalars().all()
    return [_fmt_vote(v) for v in votes]


# ── Execution ─────────────────────────────────────────────────────────────────

@router.post("/proposals/{proposal_id}/execute", summary="Execute a passed proposal (after timelock)")
async def execute_proposal(
    proposal_id:  int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_admin),
):
    try:
        proposal = await svc.execute_proposal(db, proposal_id, current_user.id)
        return _fmt_proposal(proposal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Governance Config ─────────────────────────────────────────────────────────

@router.get("/config", summary="List all protocol configuration parameters")
async def list_config(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    await svc.seed_default_config(db)
    configs = await svc.list_configs(db)
    return [_fmt_config(c) for c in configs]


@router.patch("/config/{key}", summary="Admin: update a protocol parameter")
async def update_config(
    key:          str,
    body:         ConfigUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_admin),
):
    try:
        cfg = await svc.update_config(db, key, body.value, current_user.id)
        return _fmt_config(cfg)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Tally refresh ─────────────────────────────────────────────────────────────

@router.post("/admin/refresh-tallies", summary="Admin: refresh expired proposal statuses")
async def refresh_tallies(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_admin),
):
    updated = await svc.refresh_proposal_statuses(db)
    return {"updated_proposals": updated}


# ── Summary stats ─────────────────────────────────────────────────────────────

@router.get("/stats", summary="Governance platform statistics")
async def governance_stats(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    from sqlalchemy import func, select
    from app.modules.governance.models import Proposal, Vote
    total_proposals  = (await db.execute(select(func.count(Proposal.id)))).scalar() or 0
    active_proposals = (await db.execute(
        select(func.count(Proposal.id)).where(Proposal.status == "active")
    )).scalar() or 0
    passed_proposals = (await db.execute(
        select(func.count(Proposal.id)).where(Proposal.status.in_(["passed", "executed"]))
    )).scalar() or 0
    total_votes      = (await db.execute(select(func.count(Vote.id)))).scalar() or 0
    total_power      = (await db.execute(select(func.sum(Vote.voting_power)))).scalar() or 0

    return {
        "total_proposals":  total_proposals,
        "active_proposals": active_proposals,
        "passed_proposals": passed_proposals,
        "rejected_proposals": total_proposals - active_proposals - passed_proposals,
        "total_votes":      total_votes,
        "total_voting_power_cast": float(total_power),
    }
