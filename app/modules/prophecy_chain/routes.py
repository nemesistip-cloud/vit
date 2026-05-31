"""app/modules/prophecy_chain/routes.py — Prophecy Chain API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.modules.prophecy_chain.models import ProphecyChapter, UserProphecyProgress
from app.db.models import User

router = APIRouter(prefix="/prophecy", tags=["Prophecy Chain"])

@router.get("/chapters")
async def get_chapters(db: AsyncSession = Depends(get_db)):
    """Get all Prophecy Chapters in sequence."""
    res = await db.execute(select(ProphecyChapter).order_by(ProphecyChapter.sequence_order))
    return res.scalars().all()

@router.get("/status")
async def get_user_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's Prophecy Chain progress."""
    res = await db.execute(
        select(UserProphecyProgress).where(UserProphecyProgress.user_id == current_user.id)
    )
    progress = res.scalar_one_or_none()

    if not progress:
        # Initial empty state
        return {
            "current_chapter_id": None,
            "chapters_completed": [],
            "total_qualified_predictions": 0,
            "current_accuracy": 0.0,
            "is_enrolled": False
        }

    return progress
