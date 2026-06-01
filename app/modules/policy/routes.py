from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from .models import PolicyImpact

router = APIRouter(prefix="/policy", tags=["Policy"])

@router.get("/impacts")
async def get_policy_impacts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PolicyImpact))
    return result.scalars().all()
