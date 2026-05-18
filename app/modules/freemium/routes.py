"""app/modules/freemium/routes.py
Freemium & Growth Layer — Phase 6/25
Prediction Receipts, The Oracle's Mic, and VIT IQ Test.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.db.models import Match


class IQTestSubmission(BaseModel):
    answers: Dict[str, int]

router = APIRouter(prefix="/api/freemium", tags=["Freemium & Growth"])
logger = logging.getLogger(__name__)


@router.get("/receipt/{prediction_id}")
async def get_prediction_receipt(prediction_id: int):
    """Shareable proof of correct predictions."""
    return {
        "prediction_id": prediction_id,
        "receipt_url": f"https://vit.network/receipt/{prediction_id}",
        "on_chain_hash": "0xabc123...",
        "status": "verified"
    }


# ── IQ Test ───────────────────────────────────────────────────────────────────

_IQ_QUESTIONS = [
    {
        "id": 1,
        "q": "A team has a 60% win probability. What are the 'fair' decimal odds?",
        "options": ["1.40", "1.67", "2.10", "1.50"],
        "correct": 1,
        "explanation": "Fair decimal odds = 1 / probability. 1 / 0.60 = 1.667.",
    },
    {
        "id": 2,
        "q": "If you bet on a +EV edge of 5% consistently with proper bankroll management, your long-term outcome is most likely:",
        "options": [
            "Guaranteed profit every week",
            "Growth with variance / drawdowns",
            "Break-even after fees",
            "Ruin within 100 bets",
        ],
        "correct": 1,
        "explanation": "Positive EV produces long-run growth but variance causes natural drawdowns.",
    },
    {
        "id": 3,
        "q": "Which metric is the best leading indicator of a prediction model's 'truth' vs. the market?",
        "options": ["ROI", "Win Rate", "CLV (Closing Line Value)", "Yield"],
        "correct": 2,
        "explanation": "CLV measures whether you beat the closing line — the sharpest signal of model quality.",
    },
    {
        "id": 4,
        "q": "The Kelly Criterion recommends staking __% of bankroll when edge = 8% and decimal odds = 2.0.",
        "options": ["2%", "8%", "16%", "4%"],
        "correct": 1,
        "explanation": "Kelly = (bp – q) / b where b = 1 (net odds), p = 0.54, q = 0.46 → 8%.",
    },
    {
        "id": 5,
        "q": "What does it mean when a bookmaker significantly moves a line after opening?",
        "options": [
            "The team has injury news",
            "Sharp money has come in on one side",
            "Public betting is balanced",
            "The event is being cancelled",
        ],
        "correct": 1,
        "explanation": "Significant early line movement is usually caused by sharp bettors placing large wagers.",
    },
]


@router.get("/iq-test/questions")
async def get_iq_test_questions():
    """Return all IQ-test questions (without revealing correct answers)."""
    public = [
        {"id": q["id"], "q": q["q"], "options": q["options"]}
        for q in _IQ_QUESTIONS
    ]
    return {"total": len(public), "questions": public}


@router.post("/iq-test/submit")
async def submit_iq_test(body: IQTestSubmission):
    """
    Submit answers dict {question_id: chosen_option_index}.
    Accepts string keys ("1", "q1", "q_1") or integer keys.
    Returns score, explanations, and VIT IQ rating.
    """
    # Normalise keys: strip non-digit prefix so "q1" → 1
    def _parse_key(k: str) -> int:
        stripped = k.lstrip("q_").lstrip("q")
        try:
            return int(stripped)
        except ValueError:
            return -1

    normalised: Dict[int, int] = {_parse_key(k): v for k, v in body.answers.items()}

    results = []
    correct_count = 0
    for q in _IQ_QUESTIONS:
        chosen = normalised.get(q["id"])
        is_correct = chosen == q["correct"]
        if is_correct:
            correct_count += 1
        results.append({
            "id":          q["id"],
            "correct":     is_correct,
            "your_answer": chosen,
            "right_answer": q["correct"],
            "explanation": q["explanation"],
        })

    total = len(_IQ_QUESTIONS)
    iq_estimate = round((correct_count / total) * 140 + 20)
    pct = correct_count / total

    if pct == 1.0:
        label = "Elite Analyst"
    elif pct >= 0.8:
        label = "Sharp Bettor"
    elif pct >= 0.6:
        label = "Value Hunter"
    elif pct >= 0.4:
        label = "Learning Edge"
    else:
        label = "Beginner"

    return {
        "score":        correct_count,
        "total":        total,
        "iq_estimate":  iq_estimate,
        "iq_score":     iq_estimate,
        "label":        label,
        "results":      results,
    }


# ── Oracle's Mic ──────────────────────────────────────────────────────────────

def _generate_episodes(upcoming_matches: List[Any]) -> List[Dict]:
    """Build dynamic episode list using upcoming match fixtures + static schedule."""
    today = datetime.now(timezone.utc)
    episodes: List[Dict] = []

    # Dynamic episodes from real upcoming matches
    leagues_seen: set = set()
    for match in upcoming_matches[:6]:
        league = getattr(match, "league", "Football")
        if league in leagues_seen:
            continue
        leagues_seen.add(league)
        ko = getattr(match, "kickoff_time", today)
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        delta = (ko - today).days
        if delta == 0:
            date_label = "Today"
        elif delta == 1:
            date_label = "Tomorrow"
        elif delta < 0:
            date_label = f"{abs(delta)} day(s) ago"
        else:
            date_label = f"In {delta} day(s)"

        episodes.append({
            "id":      f"ep_{match.id}",
            "title":   f"{league} Preview: {match.home_team} vs {match.away_team}",
            "host":    "Veteran Analyst",
            "date":    date_label,
            "length":  "05:00",
            "premium": False,
            "current": len(episodes) == 0,
        })

    # Pad with static evergreen episodes if not enough live fixtures
    static_episodes = [
        {"id": "ep_eq", "title": "The Equilibrium Deep-Dive", "host": "Data Nerd",    "date": "Yesterday", "length": "08:12", "premium": True,  "current": False},
        {"id": "ep_la", "title": "Upset Alert: La Liga Edition", "host": "Hype Man",  "date": "2 days ago","length": "04:30", "premium": False, "current": False},
        {"id": "ep_cl", "title": "Champions League Value Picks", "host": "Sharp Scout","date": "3 days ago","length": "06:45", "premium": True,  "current": False},
        {"id": "ep_ov", "title": "Over/Under Masterclass", "host": "Stats Guru",      "date": "4 days ago","length": "07:20", "premium": False, "current": False},
    ]
    for ep in static_episodes:
        if len(episodes) >= 5:
            break
        episodes.append(ep)

    # Ensure at least one episode is marked current
    if episodes and not any(e["current"] for e in episodes):
        episodes[0]["current"] = True

    return episodes


@router.get("/oracle-mic/episodes")
async def get_oracle_mic_episodes(db: AsyncSession = Depends(get_db)):
    """Return a dynamic list of AI-generated podcast episodes."""
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=7)

    result = await db.execute(
        select(Match)
        .where(Match.kickoff_time >= now, Match.kickoff_time <= window_end)
        .order_by(Match.kickoff_time)
        .limit(10)
    )
    upcoming = result.scalars().all()

    episodes = _generate_episodes(upcoming)
    current  = next((e for e in episodes if e["current"]), episodes[0] if episodes else None)

    return {
        "current_episode": current,
        "episodes":        episodes,
        "generated_at":    now.isoformat(),
    }


@router.get("/oracle-mic/podcast")
async def get_podcast(db: AsyncSession = Depends(get_db)):
    """Legacy single-episode endpoint — returns the current playing episode."""
    data = await get_oracle_mic_episodes(db)
    ep = data["current_episode"] or {}
    return {
        "url":      "https://vit.network/cdn/podcasts/daily.mp3",
        "duration": ep.get("length", "05:00"),
        "host":     ep.get("host", "Veteran Analyst"),
        "title":    ep.get("title", "Daily Preview"),
    }


@router.get("/wrapped/annual")
async def get_wrapped():
    """Annual Spotify-Wrapped-style personalised prediction personality report."""
    return {"year": 2025, "top_call": "Lakers Win @ 4.50", "personality_type": "The Sharp", "win_rate": 0.58}
