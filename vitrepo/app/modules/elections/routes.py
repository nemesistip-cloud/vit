from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from .models import ElectionEvent
from .services import ElectionService

router = APIRouter(prefix="/elections", tags=["Elections"])

@router.get("/events")
async def get_election_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ElectionEvent))
    return result.scalars().all()

@router.post("/events/{election_id}/analyze")
async def analyze_election_sentiment(election_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ElectionEvent).where(ElectionEvent.id == election_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Election not found")

    sentiment = await ElectionService.run_sentiment_analysis(db, election_id)
    return {"status": "success", "sentiment": sentiment}
