"""
app/modules/watchlist/routes.py — Watchlist module-level router.

Provides CRUD endpoints for WatchlistItem using SQLAlchemy async sessions.
The API-level router at app/api/routes/watchlist.py delegates to these endpoints;
this module-level router makes the watchlist module self-contained.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_

from app.db.database import get_db
from app.modules.watchlist.models import WatchlistItem
from app.db.models import Match, User
from app.api.deps import get_current_user

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get(
    "",
    summary="List watchlist",
    response_description="Matches the current user has bookmarked",
)
async def list_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all WatchlistItems (with their associated Match) for the current user."""
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == current_user.id)
    )
    items = result.scalars().all()
    return {"items": [{"id": item.id, "match_id": item.match_id, "created_at": item.created_at.isoformat()} for item in items]}


@router.post(
    "/{match_id}",
    summary="Add to watchlist",
    status_code=201,
)
async def add_to_watchlist(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a match to the current user's watchlist (idempotent)."""
    existing = (
        await db.execute(
            select(WatchlistItem).where(
                and_(
                    WatchlistItem.user_id == current_user.id,
                    WatchlistItem.match_id == match_id,
                )
            )
        )
    ).scalar_one_or_none()

    if existing:
        return {"success": True, "message": "Already in watchlist.", "id": existing.id}

    # Verify the match exists
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")

    item = WatchlistItem(user_id=current_user.id, match_id=match_id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "id": item.id, "match_id": match_id}


@router.delete(
    "/{match_id}",
    summary="Remove from watchlist",
)
async def remove_from_watchlist(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a match from the current user's watchlist."""
    await db.execute(
        delete(WatchlistItem).where(
            and_(
                WatchlistItem.user_id == current_user.id,
                WatchlistItem.match_id == match_id,
            )
        )
    )
    await db.commit()
    return {"success": True}


@router.get(
    "/health",
    include_in_schema=False,
)
async def health():
    return {"status": "ok"}
