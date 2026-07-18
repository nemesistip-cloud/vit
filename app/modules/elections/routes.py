# app/modules/elections/routes.py
"""Electoral & Policy Simulator — API routes (TRACK-015)."""

import uuid
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.api.deps import get_current_user, get_current_admin
from app.db.models import User

from .models import (
    Election, ElectionStatus, ElectionType,
    Candidate, ElectionPoll, ElectionPrediction,
    PolicyProposal, PolicyCategory, PolicyStatus,
    ElectionEvent,
)
from .services import (
    ElectionService,
    get_election,
    create_election,
    aggregate_polls,
    run_simulation,
    score_policy,
)

router = APIRouter(tags=["Elections"])


# ── Elections ────────────────────────────────────────────────────────────────

@router.post("/api/elections", status_code=status.HTTP_201_CREATED)
async def create_election_endpoint(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Create a new election (admin only)."""
    required = ("title", "country", "election_type", "election_date")
    for field in required:
        if field not in payload:
            raise HTTPException(status_code=422, detail=f"Missing field: {field}")

    # Parse election_date if string
    if isinstance(payload.get("election_date"), str):
        payload["election_date"] = date.fromisoformat(payload["election_date"])

    election = await create_election(payload, db)
    return _election_dict(election)


@router.get("/api/elections")
async def list_elections(
    status_filter: Optional[str] = Query(None, alias="status"),
    country: Optional[str] = Query(None),
    election_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List elections with optional filters."""
    q = select(Election)
    if status_filter:
        q = q.where(Election.status == status_filter)
    if country:
        q = q.where(Election.country == country.upper())
    if election_type:
        q = q.where(Election.election_type == election_type)
    result = await db.execute(q.order_by(Election.election_date.desc()))
    elections = result.scalars().all()
    return [_election_dict(e) for e in elections]


@router.get("/api/elections/{election_id}")
async def get_election_detail(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get election detail including poll aggregate."""
    election = await get_election(election_id, db)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    aggregated = await aggregate_polls(election_id, db)
    data = _election_dict(election)
    data["poll_aggregate"] = aggregated
    return data


# ── Candidates ───────────────────────────────────────────────────────────────

@router.post("/api/elections/{election_id}/candidates", status_code=status.HTTP_201_CREATED)
async def add_candidate(
    election_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Add a candidate to an election (admin only)."""
    election = await get_election(election_id, db)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    required = ("name", "party")
    for field in required:
        if field not in payload:
            raise HTTPException(status_code=422, detail=f"Missing field: {field}")

    candidate = Candidate(
        election_id=election_id,
        name=payload["name"],
        party=payload["party"],
        position=payload.get("position"),
        bio=payload.get("bio"),
        polling_avg=float(payload.get("polling_avg", 0.0)),
        win_probability=float(payload.get("win_probability", 0.0)),
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return _candidate_dict(candidate)


@router.get("/api/elections/{election_id}/candidates")
async def list_candidates(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List candidates with win probabilities."""
    election = await get_election(election_id, db)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    return [_candidate_dict(c) for c in election.candidates]


# ── Polls ────────────────────────────────────────────────────────────────────

@router.post("/api/elections/{election_id}/polls", status_code=status.HTTP_201_CREATED)
async def submit_poll(
    election_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Submit a poll for an election (admin only)."""
    election = await get_election(election_id, db)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    required = ("pollster", "conducted_date", "sample_size", "results")
    for field in required:
        if field not in payload:
            raise HTTPException(status_code=422, detail=f"Missing field: {field}")

    conducted = payload["conducted_date"]
    if isinstance(conducted, str):
        conducted = date.fromisoformat(conducted)

    poll = ElectionPoll(
        election_id=election_id,
        pollster=payload["pollster"],
        conducted_date=conducted,
        sample_size=int(payload["sample_size"]),
        methodology=payload.get("methodology"),
        margin_of_error=float(payload.get("margin_of_error", 3.0)),
        results=payload["results"],
        weight=float(payload.get("weight", 1.0)),
    )
    db.add(poll)
    await db.commit()
    await db.refresh(poll)
    return _poll_dict(poll)


@router.get("/api/elections/{election_id}/polls")
async def list_polls(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List polls for an election."""
    election = await get_election(election_id, db)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    return [_poll_dict(p) for p in election.polls]


# ── Simulation ───────────────────────────────────────────────────────────────

@router.get("/api/elections/{election_id}/simulate")
async def simulate_seats(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run D'Hondt seat projection + swing scenarios (±5%)."""
    election = await get_election(election_id, db)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    result = await run_simulation(election_id, db)
    return {
        "election_id": election_id,
        "seat_projection": result.get("seat_projection", {}),
        "swing_scenarios": result.get("swing_scenarios", {}),
        "poll_aggregation": result.get("poll_aggregation", {}),
    }


@router.get("/api/elections/{election_id}/probability")
async def win_probability(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Monte Carlo win probabilities for all candidates."""
    election = await get_election(election_id, db)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    result = await run_simulation(election_id, db)
    return {
        "election_id": election_id,
        "monte_carlo": result.get("monte_carlo", []),
    }


# ── Predictions ──────────────────────────────────────────────────────────────

@router.post("/api/elections/{election_id}/predictions", status_code=status.HTTP_201_CREATED)
async def submit_prediction(
    election_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a user prediction for an election."""
    election = await get_election(election_id, db)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    if "predicted_outcome" not in payload:
        raise HTTPException(status_code=422, detail="Missing field: predicted_outcome")

    prediction = ElectionPrediction(
        election_id=election_id,
        user_id=current_user.id,
        candidate_id=payload.get("candidate_id"),
        predicted_outcome=payload["predicted_outcome"],
        reasoning=payload.get("reasoning"),
    )
    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)
    return _prediction_dict(prediction)


@router.get("/api/elections/{election_id}/predictions")
async def community_predictions(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Aggregate community predictions for an election."""
    election = await get_election(election_id, db)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    result = await db.execute(
        select(ElectionPrediction).where(ElectionPrediction.election_id == election_id)
    )
    predictions = result.scalars().all()

    # Aggregate: count predictions per candidate_id
    tally: dict[str, int] = {}
    total = len(predictions)
    for p in predictions:
        cid = p.candidate_id or "__other__"
        tally[cid] = tally.get(cid, 0) + 1

    community_pct = {
        cid: round(count / total * 100, 2) if total > 0 else 0.0
        for cid, count in tally.items()
    }

    return {
        "election_id": election_id,
        "total_predictions": total,
        "community_pick_percentages": community_pct,
        "predictions": [_prediction_dict(p) for p in predictions],
    }


# ── Policy ───────────────────────────────────────────────────────────────────

@router.post("/api/policy", status_code=status.HTTP_201_CREATED)
async def create_policy(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Create a policy proposal (admin only)."""
    required = ("title", "jurisdiction", "category", "description", "sponsor")
    for field in required:
        if field not in payload:
            raise HTTPException(status_code=422, detail=f"Missing field: {field}")

    policy = PolicyProposal(
        title=payload["title"],
        jurisdiction=payload["jurisdiction"],
        category=payload["category"],
        description=payload["description"],
        sponsor=payload["sponsor"],
        status=payload.get("status", PolicyStatus.draft),
        impact_scores=payload.get("impact_scores"),
        metadata_=payload.get("metadata"),
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return _policy_dict(policy)


@router.get("/api/policy")
async def list_policies(
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    jurisdiction: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List policy proposals with optional filters."""
    q = select(PolicyProposal)
    if category:
        q = q.where(PolicyProposal.category == category)
    if status_filter:
        q = q.where(PolicyProposal.status == status_filter)
    if jurisdiction:
        q = q.where(PolicyProposal.jurisdiction == jurisdiction)
    result = await db.execute(q.order_by(PolicyProposal.created_at.desc()))
    policies = result.scalars().all()
    return [_policy_dict(p) for p in policies]


@router.get("/api/policy/{policy_id}")
async def get_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get policy detail with impact scores."""
    result = await db.execute(
        select(PolicyProposal).where(PolicyProposal.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_dict(policy)


@router.post("/api/policy/{policy_id}/score")
async def recompute_policy_score(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """(Re)compute impact scores for a policy via PolicyScorer (admin only)."""
    result = await db.execute(
        select(PolicyProposal).where(PolicyProposal.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    scores = await score_policy(policy_id, db)
    return {
        "policy_id": policy_id,
        "impact_scores": scores,
    }


# ── Legacy endpoints (preserved) ─────────────────────────────────────────────

@router.get("/elections/events")
async def get_election_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ElectionEvent))
    return result.scalars().all()


@router.post("/elections/events/{election_id}/analyze")
async def analyze_election_sentiment(election_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ElectionEvent).where(ElectionEvent.id == election_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Election not found")
    sentiment = await ElectionService.run_sentiment_analysis(db, election_id)
    return {"status": "success", "sentiment": sentiment}


# ── Serializer helpers ────────────────────────────────────────────────────────

def _election_dict(e: Election) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "country": e.country,
        "election_type": e.election_type.value if hasattr(e.election_type, "value") else e.election_type,
        "election_date": e.election_date.isoformat() if e.election_date else None,
        "status": e.status.value if hasattr(e.status, "value") else e.status,
        "description": e.description,
        "total_seats": e.total_seats,
        "metadata": e.metadata_,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _candidate_dict(c: Candidate) -> dict:
    return {
        "id": c.id,
        "election_id": c.election_id,
        "name": c.name,
        "party": c.party,
        "position": c.position,
        "bio": c.bio,
        "polling_avg": c.polling_avg,
        "win_probability": c.win_probability,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _poll_dict(p: ElectionPoll) -> dict:
    return {
        "id": p.id,
        "election_id": p.election_id,
        "pollster": p.pollster,
        "conducted_date": p.conducted_date.isoformat() if p.conducted_date else None,
        "sample_size": p.sample_size,
        "methodology": p.methodology,
        "margin_of_error": p.margin_of_error,
        "results": p.results,
        "weight": p.weight,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _prediction_dict(p: ElectionPrediction) -> dict:
    return {
        "id": p.id,
        "election_id": p.election_id,
        "user_id": p.user_id,
        "candidate_id": p.candidate_id,
        "predicted_outcome": p.predicted_outcome,
        "reasoning": p.reasoning,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _policy_dict(p: PolicyProposal) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "jurisdiction": p.jurisdiction,
        "category": p.category.value if hasattr(p.category, "value") else p.category,
        "description": p.description,
        "sponsor": p.sponsor,
        "status": p.status.value if hasattr(p.status, "value") else p.status,
        "impact_scores": p.impact_scores,
        "metadata": p.metadata_,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
