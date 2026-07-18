# app/modules/elections/services.py
"""Service layer for Electoral & Policy Simulator (TRACK-015)."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from .models import (
    Election, Candidate, ElectionPoll, ElectionPrediction,
    PolicyProposal, ElectionEvent, PollingData,
)
from .simulator import PollAggregator, SeatProjector, OutcomeSimulator, PolicyScorer

# ── Legacy service (preserved) ────────────────────────────────────────────────
from app.services.web_search import _ddg_search
from app.services.ai_client import call_ai
import random
import json


class ElectionService:
    @staticmethod
    async def run_sentiment_analysis(db: AsyncSession, election_id: int):
        result = await db.execute(select(ElectionEvent).where(ElectionEvent.id == election_id))
        election = result.scalar_one_or_none()
        if not election:
            return None

        candidates_str = (
            ", ".join(election.candidates.keys())
            if isinstance(election.candidates, dict)
            else str(election.candidates)
        )
        query = f"election sentiment {election.title} {election.country} {candidates_str}"
        news_snippets = await _ddg_search(query, max_results=8)

        news_context = "\n".join([f"- {s}" for s in news_snippets])
        prompt = f"""Analyze the electoral sentiment for the following election event.
Event: {election.title}
Country: {election.country}
Candidates: {candidates_str}

Recent News Context:
{news_context}

Return ONLY a JSON object (no markdown):
{{
  "scores": {{ "candidate_name": 0.XX, ... }},
  "rationale": "short explanation",
  "data_points_analyzed": {len(news_snippets)}
}}"""

        ai_response = await call_ai(prompt)
        try:
            clean_response = ai_response.strip().replace("```json", "").replace("```", "").strip()
            sentiment_data = json.loads(clean_response)
        except Exception:
            sentiment_data = {
                "scores": {k: round(random.uniform(0.3, 0.5), 2) for k in election.candidates.keys()},
                "rationale": "Simulated fallback due to AI response error.",
                "data_points_analyzed": len(news_snippets),
            }

        from datetime import datetime, timezone
        await db.execute(
            update(ElectionEvent)
            .where(ElectionEvent.id == election_id)
            .values(sentiment_data={
                **sentiment_data,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            })
        )
        await db.commit()
        return sentiment_data


# ── TRACK-015 service helpers ─────────────────────────────────────────────────

async def get_election(election_id: str, db: AsyncSession) -> Optional[Election]:
    result = await db.execute(
        select(Election)
        .options(
            selectinload(Election.candidates),
            selectinload(Election.polls),
        )
        .where(Election.id == election_id)
    )
    return result.scalar_one_or_none()


async def create_election(data: dict, db: AsyncSession) -> Election:
    election = Election(
        title=data["title"],
        country=data["country"],
        election_type=data["election_type"],
        election_date=data["election_date"],
        status=data.get("status", "upcoming"),
        description=data.get("description"),
        total_seats=data.get("total_seats"),
        metadata_=data.get("metadata"),
    )
    db.add(election)
    await db.commit()
    await db.refresh(election)
    return election


async def aggregate_polls(election_id: str, db: AsyncSession) -> dict:
    result = await db.execute(
        select(ElectionPoll).where(ElectionPoll.election_id == election_id)
    )
    polls = result.scalars().all()
    if not polls:
        return {}

    poll_dicts = [
        {
            "conducted_date": p.conducted_date,
            "sample_size": p.sample_size,
            "margin_of_error": p.margin_of_error,
            "results": p.results,
            "weight": p.weight,
        }
        for p in polls
    ]
    aggregator = PollAggregator()
    aggregated = aggregator.aggregate(poll_dicts)

    # Persist polling_avg back onto each candidate
    if aggregated:
        cand_result = await db.execute(
            select(Candidate).where(Candidate.election_id == election_id)
        )
        candidates = cand_result.scalars().all()
        for c in candidates:
            if c.id in aggregated:
                c.polling_avg = aggregated[c.id]
        await db.commit()

    return aggregated


async def run_simulation(election_id: str, db: AsyncSession) -> dict:
    election = await get_election(election_id, db)
    if not election:
        return {}

    aggregated = await aggregate_polls(election_id, db)

    # Build vote_shares for D'Hondt from candidates
    candidates = election.candidates
    vote_shares: dict[str, float] = {}
    candidate_inputs: list[dict] = []

    for c in candidates:
        pct = aggregated.get(c.id, c.polling_avg or 0.0)
        vote_shares[c.id] = pct
        # Find the max margin_of_error across all polls for this election
        candidate_inputs.append({
            "candidate_id": c.id,
            "poll_pct": pct,
            "margin_of_error": 3.0,
        })

    # D'Hondt projection (only meaningful when election has total_seats)
    total_seats = election.total_seats or 0
    projector = SeatProjector()
    seat_projection: dict[str, int] = {}
    swing_scenarios: dict[str, dict] = {}

    if total_seats > 0 and vote_shares:
        # Use party names mapped from candidates for D'Hondt
        party_shares: dict[str, float] = {}
        party_to_candidate: dict[str, str] = {}
        for c in candidates:
            party = c.party
            pct = vote_shares.get(c.id, 0.0)
            party_shares[party] = party_shares.get(party, 0.0) + pct
            party_to_candidate[party] = c.id

        seat_projection = projector.project(party_shares, total_seats)

        for party in party_shares:
            swing_scenarios[f"{party}_minus5"] = projector.swing_scenario(
                party_shares, party, -5.0, total_seats
            )
            swing_scenarios[f"{party}_plus5"] = projector.swing_scenario(
                party_shares, party, +5.0, total_seats
            )

    # Monte Carlo win probabilities
    # Get average margin_of_error from polls
    poll_result = await db.execute(
        select(ElectionPoll).where(ElectionPoll.election_id == election_id)
    )
    polls = poll_result.scalars().all()
    avg_moe = (
        sum(p.margin_of_error for p in polls) / len(polls) if polls else 3.0
    )
    for ci in candidate_inputs:
        ci["margin_of_error"] = avg_moe

    simulator = OutcomeSimulator()
    mc_results = simulator.monte_carlo(candidate_inputs, n_sims=5000)

    # Persist win_probability back to candidates
    win_map = {r["candidate_id"]: r["win_prob"] for r in mc_results}
    for c in candidates:
        if c.id in win_map:
            c.win_probability = win_map[c.id]
    await db.commit()

    return {
        "seat_projection": seat_projection,
        "swing_scenarios": swing_scenarios,
        "monte_carlo": mc_results,
        "poll_aggregation": aggregated,
    }


async def score_policy(policy_id: str, db: AsyncSession) -> dict:
    result = await db.execute(
        select(PolicyProposal).where(PolicyProposal.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        return {}

    scorer = PolicyScorer()
    keywords = (policy.description or "").lower().split()
    # Also include title words
    keywords += (policy.title or "").lower().split()
    scores = scorer.score(policy.category.value if hasattr(policy.category, "value") else policy.category, keywords)

    policy.impact_scores = scores
    await db.commit()
    return scores
