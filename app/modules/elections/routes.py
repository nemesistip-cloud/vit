from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from .models import ElectionEvent

router = APIRouter(prefix="/elections", tags=["Elections"])

@router.get("/events")
async def get_election_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ElectionEvent))
    return result.scalars().all()
