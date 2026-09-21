"""app/modules/prophecy_chain/routes.py — Prophecy Chain API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List
from datetime import datetime, timezone

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.modules.prophecy_chain.models import ProphecyChapter, UserProphecyProgress
from app.db.models import User, Prediction
from app.modules.wallet.services import WalletService

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

    # Compute stats from Prediction table
    total_qualified = (await db.execute(
        select(func.count(Prediction.id)).where(
            and_(Prediction.user_id == current_user.id, Prediction.was_correct.is_not(None))
        )
    )).scalar() or 0

    settled_wins = (await db.execute(
        select(func.count(Prediction.id)).where(
            and_(Prediction.user_id == current_user.id, Prediction.was_correct == True)
        )
    )).scalar() or 0

    accuracy = settled_wins / total_qualified if total_qualified > 0 else 0.0

    if not progress:
        return {
            "current_chapter_id": None,
            "chapters_completed": [],
            "total_qualified_predictions": total_qualified,
            "current_accuracy": accuracy,
            "is_enrolled": False
        }

    return {
        "current_chapter_id": progress.current_chapter_id,
        "chapters_completed": progress.chapters_completed,
        "total_qualified_predictions": total_qualified,
        "current_accuracy": accuracy,
        "is_enrolled": True
    }

@router.post("/enroll")
async def enroll_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enroll authenticated user in Prophecy Chain."""
    res = await db.execute(
        select(UserProphecyProgress).where(UserProphecyProgress.user_id == current_user.id)
    )
    progress = res.scalar_one_or_none()

    if progress:
        return {"enrolled": True, "chapter_id": progress.current_chapter_id}

    # Get lowest sequence chapter
    res = await db.execute(
        select(ProphecyChapter).where(ProphecyChapter.is_active == True).order_by(ProphecyChapter.sequence_order).limit(1)
    )
    first_chapter = res.scalar_one_or_none()

    if not first_chapter:
        raise HTTPException(status_code=404, detail="No chapters available for enrollment.")

    progress = UserProphecyProgress(
        user_id=current_user.id,
        current_chapter_id=first_chapter.id,
        chapters_completed=[],
        chapters_claimed=[]
    )
    db.add(progress)
    await db.commit()

    return {"enrolled": True, "chapter_id": first_chapter.id}

@router.post("/chapters/{chapter_id}/complete")
async def complete_chapter(
    chapter_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a chapter as complete for the user."""
    res = await db.execute(
        select(UserProphecyProgress).where(UserProphecyProgress.user_id == current_user.id)
    )
    progress = res.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=400, detail="User not enrolled in Prophecy Chain.")

    res = await db.execute(select(ProphecyChapter).where(ProphecyChapter.id == chapter_id))
    chapter = res.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found.")

    if chapter_id in progress.chapters_completed:
        return {"success": True, "message": "Chapter already completed."}

    # Validate requirements
    total_qualified = (await db.execute(
        select(func.count(Prediction.id)).where(
            and_(Prediction.user_id == current_user.id, Prediction.was_correct.is_not(None))
        )
    )).scalar() or 0

    settled_wins = (await db.execute(
        select(func.count(Prediction.id)).where(
            and_(Prediction.user_id == current_user.id, Prediction.was_correct == True)
        )
    )).scalar() or 0

    accuracy = settled_wins / total_qualified if total_qualified > 0 else 0.0

    if total_qualified < chapter.required_predictions:
        raise HTTPException(status_code=400, detail=f"Requirement not met: {total_qualified}/{chapter.required_predictions} predictions.")
    if accuracy < chapter.required_accuracy:
        raise HTTPException(status_code=400, detail=f"Requirement not met: {accuracy*100:.1f}%/{chapter.required_accuracy*100:.1f}% accuracy.")

    # Mark as complete
    completed = list(progress.chapters_completed)
    if chapter_id not in completed:
        completed.append(chapter_id)
        progress.chapters_completed = completed

    # Advance to next chapter
    res = await db.execute(
        select(ProphecyChapter)
        .where(and_(ProphecyChapter.sequence_order > chapter.sequence_order, ProphecyChapter.is_active == True))
        .order_by(ProphecyChapter.sequence_order)
        .limit(1)
    )
    next_chapter = res.scalar_one_or_none()
    next_chapter_id = next_chapter.id if next_chapter else None
    progress.current_chapter_id = next_chapter_id

    # Record stats at completion
    progress.total_qualified_predictions = total_qualified
    progress.total_qualified_wins = settled_wins
    progress.current_accuracy = accuracy
    progress.last_evaluated_at = datetime.now(timezone.utc)

    # Award rewards
    wallet_service = WalletService(db)
    await wallet_service.deposit_vitcoin(
        user_id=current_user.id,
        amount=chapter.reward_vit,
        description=f"Prophecy Chapter {chapter_id} reward",
        tx_type="PROPHECY_REWARD",
        metadata={"chapter_id": chapter_id}
    )

    current_user.total_xp += (chapter.reward_xp or 0)

    # Mark as claimed too since we credit them now
    claimed = list(progress.chapters_claimed or [])
    if chapter_id not in claimed:
        claimed.append(chapter_id)
        progress.chapters_claimed = claimed

    await db.commit()

    return {
        "success": True,
        "next_chapter_id": next_chapter_id,
        "rewards": {"vit": float(chapter.reward_vit), "xp": chapter.reward_xp}
    }

@router.post("/chapters/{chapter_id}/claim")
async def claim_rewards(
    chapter_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Claim rewards for a completed chapter (idempotent)."""
    res = await db.execute(
        select(UserProphecyProgress).where(UserProphecyProgress.user_id == current_user.id)
    )
    progress = res.scalar_one_or_none()
    if not progress or chapter_id not in progress.chapters_completed:
        raise HTTPException(status_code=400, detail="Chapter not completed.")

    claimed = list(progress.chapters_claimed or [])
    if chapter_id in claimed:
        return {"success": True, "message": "Rewards already claimed."}

    res = await db.execute(select(ProphecyChapter).where(ProphecyChapter.id == chapter_id))
    chapter = res.scalar_one_or_none()

    # Credit rewards
    wallet_service = WalletService(db)
    await wallet_service.deposit_vitcoin(
        user_id=current_user.id,
        amount=chapter.reward_vit,
        description=f"Prophecy Chapter {chapter_id} reward",
        tx_type="PROPHECY_REWARD",
        metadata={"chapter_id": chapter_id}
    )
    current_user.total_xp += (chapter.reward_xp or 0)

    claimed.append(chapter_id)
    progress.chapters_claimed = claimed
    await db.commit()

    return {
        "success": True,
        "rewards": {"vit": float(chapter.reward_vit), "xp": chapter.reward_xp}
    }
