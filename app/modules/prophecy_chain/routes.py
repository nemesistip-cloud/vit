from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user
from app.modules.prophecy_chain.services.prophecy_service import ProphecyService
from typing import List, Any

router = APIRouter(prefix="/api/prophecy", tags=["prophecy"])

@router.get("/chapters", response_model=List[Any])
async def get_chapters(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Fetch all chapters with user-specific progress."""
    try:
        return await ProphecyService.get_chapters_for_user(db, user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress")
async def get_user_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Fetch detailed user progress and metrics."""
    try:
        return await ProphecyService.get_user_stats(db, user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timeline")
async def get_timeline(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Fetch chronological prophecy event stream."""
    try:
        return await ProphecyService.get_prophecy_timeline(db, user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_prophecy_status():
    return {"status": "Prophecy Chain Module Active", "v": "7.0.0-merit-engine"}
