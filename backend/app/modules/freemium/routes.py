"""Freemium API routes for IQ Test and Oracle Mic."""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_optional_user, get_current_user
from app.modules.freemium.models import IQTestQuestion, UserIQTestResult, OracleMicEpisode

router = APIRouter(prefix="/api/freemium", tags=["Freemium"])
logger = logging.getLogger(__name__)

# ── IQ Test Endpoints ──────────────────────────────────────────────────

@router.get("/iq-test/questions")
async def get_iq_questions(db: AsyncSession = Depends(get_db)):
    """Fetch active IQ test questions."""
    stmt = select(IQTestQuestion).where(IQTestQuestion.is_active == True).order_by(IQTestQuestion.id)
    res = await db.execute(stmt)
    questions = res.scalars().all()

    return {
        "total": len(questions),
        "questions": [
            {
                "id": q.id,
                "q": q.q,
                "options": q.options
            } for q in questions
        ]
    }

@router.post("/iq-test/submit")
async def submit_iq_test(
    answers: Dict[int, int],
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Submit IQ test answers, calculate score, and save result.
    Calculation logic aligns with frontend: (score/total)*140 + 20.
    """
    # Fetch all active questions to validate
    stmt = select(IQTestQuestion).where(IQTestQuestion.is_active == True)
    res = await db.execute(stmt)
    questions = {q.id: q for q in res.scalars().all()}

    if not questions:
        raise HTTPException(status_code=404, detail="No active questions found.")

    score = 0
    total = len(questions)
    detailed_results = []

    for q_id, q in questions.items():
        user_ans = answers.get(q_id)
        is_correct = (user_ans == q.correct)
        if is_correct:
            score += 1

        detailed_results.append({
            "id": q.id,
            "correct": is_correct,
            "your_answer": user_ans if user_ans is not None else -1,
            "right_answer": q.correct,
            "explanation": q.explanation or "No explanation provided."
        })

    # IQ Score Formula: Mean 100, SD 15ish (here we use a custom sports-iq scale)
    iq_score = round((score / total) * 140 + 20) if total > 0 else 0

    label = "Beginner"
    if score == total:
        label = "Elite Analyst"
    elif score >= total * 0.8:
        label = "Sharp Bettor"
    elif score >= total * 0.5:
        label = "Value Hunter"
    elif score >= total * 0.2:
        label = "Learning Edge"

    # Persist if user is logged in
    if current_user:
        new_result = UserIQTestResult(
            user_id=current_user.id,
            score=score,
            total=total,
            iq_score=iq_score,
            label=label,
            answers=answers
        )
        db.add(new_result)
        await db.commit()
        logger.info(f"Saved IQ Test result for user {current_user.id}: {iq_score}")
    else:
        logger.info(f"Guest IQ Test submission: {iq_score}")

    return {
        "score": score,
        "total": total,
        "iq_score": iq_score,
        "label": label,
        "results": detailed_results
    }

# ── Oracle Mic Endpoints ───────────────────────────────────────────────

@router.get("/oracle-mic/episodes")
async def get_oracle_mic_episodes(db: AsyncSession = Depends(get_db)):
    """Fetch AI-generated podcast episodes."""
    stmt = (
        select(OracleMicEpisode)
        .where(OracleMicEpisode.is_active == True)
        .order_by(OracleMicEpisode.sort_order.desc(), OracleMicEpisode.created_at.desc())
    )
    res = await db.execute(stmt)
    episodes = res.scalars().all()

    current_episode = episodes[0] if episodes else None

    return {
        "current_episode": {
            "id": current_episode.id,
            "title": current_episode.title,
            "host": current_episode.host,
            "date": current_episode.date,
            "length": current_episode.length,
            "premium": current_episode.premium,
            "current": True
        } if current_episode else None,
        "episodes": [
            {
                "id": e.id,
                "title": e.title,
                "host": e.host,
                "date": e.date,
                "length": e.length,
                "premium": e.premium,
                "current": (e.id == current_episode.id if current_episode else False)
            } for e in episodes
        ],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
