from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin
from app.db.database import get_db
from app.db.models import User
from app.modules.rewards.models import OfferCompletion
from app.modules.rewards.schemas import OfferCompletionResponse, OfferCompletionUpdate

router = APIRouter(prefix="/admin/rewards", tags=["admin-rewards"])


@router.get("/", response_model=List[OfferCompletionResponse])
async def list_rewards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    status: Optional[str] = Query(None, description="Filter by status"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List reward completions with optional filtering."""
    query = select(OfferCompletion)
    
    if status:
        query = query.where(OfferCompletion.status == status)
    if provider:
        query = query.where(OfferCompletion.provider == provider)
    if user_id:
        query = query.where(OfferCompletion.user_id == user_id)
    
    query = query.order_by(OfferCompletion.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    rewards = result.scalars().all()
    return rewards


@router.get("/{reward_id}", response_model=OfferCompletionResponse)
async def get_reward(
    reward_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Get a specific reward completion by ID."""
    result = await db.execute(select(OfferCompletion).where(OfferCompletion.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    return reward


@router.patch("/{reward_id}/review", response_model=OfferCompletionResponse)
async def review_reward(
    reward_id: int,
    update_data: OfferCompletionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Review and update a reward completion (approve/reject/manual review)."""
    result = await db.execute(select(OfferCompletion).where(OfferCompletion.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    
    # Update the reward
    update_dict = update_data.model_dump(exclude_unset=True)
    if update_dict:
        update_dict["updated_at"] = "now()"  # Will be handled by SQLAlchemy
        await db.execute(
            update(OfferCompletion)
            .where(OfferCompletion.id == reward_id)
            .values(**update_dict)
        )
        await db.commit()
        await db.refresh(reward)
    
    return reward


@router.delete("/{reward_id}")
async def delete_reward(
    reward_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Delete a reward completion (for fraud removal)."""
    result = await db.execute(select(OfferCompletion).where(OfferCompletion.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    
    await db.delete(reward)
    await db.commit()
    
    return {"message": "Reward deleted successfully"}