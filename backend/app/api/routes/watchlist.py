from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import joinedload
from app.db.database import get_db
from app.modules.watchlist.models import WatchlistItem
from app.db.models import Match, User
from app.api.deps import get_current_user
from typing import List

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])

@router.get("")
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's bookmarked matches."""
    res = await db.execute(
        select(WatchlistItem)
        .options(joinedload(WatchlistItem.match))
        .where(WatchlistItem.user_id == current_user.id)
    )
    items = res.scalars().all()
    return [item.match for item in items if item.match]

@router.post("/{match_id}")
async def add_to_watchlist(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a match to watchlist (idempotent)."""
    # Check if exists
    res = await db.execute(
        select(WatchlistItem).where(
            and_(WatchlistItem.user_id == current_user.id, WatchlistItem.match_id == match_id)
        )
    )
    if res.scalar_one_or_none():
        return {"success": True, "message": "Already in watchlist."}

    # Verify match exists
    res = await db.execute(select(Match).where(Match.id == match_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Match not found.")

    item = WatchlistItem(user_id=current_user.id, match_id=match_id)
    db.add(item)
    await db.commit()
    return {"success": True}

@router.delete("/{match_id}")
async def remove_from_watchlist(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a match from watchlist."""
    await db.execute(
        delete(WatchlistItem).where(
            and_(WatchlistItem.user_id == current_user.id, WatchlistItem.match_id == match_id)
        )
    )
    await db.commit()
    return {"success": True}
