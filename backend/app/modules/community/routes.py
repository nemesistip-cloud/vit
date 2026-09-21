from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from .models import CommunityCircle, CommunityMember
from app.api.deps import get_current_user
from app.db.models import User
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/community", tags=["Community Circles"])

class CircleCreate(BaseModel):
    name: str
    category: str

@router.get("/circles")
async def list_circles(db: AsyncSession = Depends(get_db)):
    """List all community circles."""
    res = await db.execute(select(CommunityCircle))
    return res.scalars().all()

@router.post("/circles")
async def create_circle(
    body: CircleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new community circle."""
    # Check if exists
    res = await db.execute(select(CommunityCircle).where(CommunityCircle.name == body.name))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Circle name already taken.")

    circle = CommunityCircle(
        name=body.name,
        category=body.category,
        creator_id=current_user.id,
        member_count=1
    )
    db.add(circle)
    await db.flush()

    # Creator automatically joins
    member = CommunityMember(circle_id=circle.id, user_id=current_user.id)
    db.add(member)

    await db.commit()
    await db.refresh(circle)
    return circle

@router.get("/circles/{circle_id}/members")
async def list_members(circle_id: int, db: AsyncSession = Depends(get_db)):
    """List members of a circle."""
    res = await db.execute(
        select(User.username)
        .join(CommunityMember, CommunityMember.user_id == User.id)
        .where(CommunityMember.circle_id == circle_id)
    )
    return res.scalars().all()

@router.post("/circles/{circle_id}/join")
async def join_circle(
    circle_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Join a community circle."""
    # Check if already a member
    res = await db.execute(
        select(CommunityMember).where(
            CommunityMember.circle_id == circle_id,
            CommunityMember.user_id == current_user.id
        )
    )
    if res.scalar_one_or_none():
        return {"success": True, "message": "Already a member."}

    res = await db.execute(select(CommunityCircle).where(CommunityCircle.id == circle_id))
    circle = res.scalar_one_or_none()
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found.")

    member = CommunityMember(circle_id=circle_id, user_id=current_user.id)
    db.add(member)

    circle.member_count += 1

    await db.commit()
    return {"success": True}
