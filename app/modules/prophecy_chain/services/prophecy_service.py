import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.prophecy_chain.models import ProphecyChapter, UserProphecyProgress, ProphecyEvent, UserMeritSnapshot
from app.modules.prophecy_chain.engine.progression import ProgressionEngine
from typing import List

logger = logging.getLogger(__name__)

class ProphecyService:
    @staticmethod
    async def get_chapters_for_user(db: AsyncSession, user_id: int):
        """Returns all chapters with progress for the specific user."""
        # Ensure progress records exist and are up to date
        await ProgressionEngine.evaluate_user_progress(db, user_id, trigger="api_request")

        stmt = (
            select(ProphecyChapter, UserProphecyProgress)
            .outerjoin(UserProphecyProgress,
                (ProphecyChapter.id == UserProphecyProgress.chapter_id) & (UserProphecyProgress.user_id == user_id)
            )
            .where(ProphecyChapter.is_active == True)
            .order_by(ProphecyChapter.unlock_order)
        )
        result = await db.execute(stmt)
        rows = result.all()

        output = []
        for chapter, progress in rows:
            output.append({
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "description": chapter.description,
                "lore": chapter.lore,
                "tier": chapter.tier,
                "progress_data": progress.progress_data if progress else {},
                "is_completed": progress.is_completed if progress else False,
                "completed_at": progress.completed_at if progress else None,
                "unlocked": progress.unlocked if progress else (chapter.unlock_order == 0),
                "unlocked_at": progress.unlocked_at if progress else None,
                "requirements": chapter.requirements,
                "reward_config": chapter.reward_config,
                "unlock_order": chapter.unlock_order
            })
        return output

    @staticmethod
    async def get_user_stats(db: AsyncSession, user_id: int):
        """Returns summarized prophecy stats for the user."""
        metrics = await ProgressionEngine._get_user_metrics(db, user_id)

        stmt = select(UserProphecyProgress).where(
            UserProphecyProgress.user_id == user_id,
            UserProphecyProgress.is_completed == True
        )
        result = await db.execute(stmt)
        completed_count = len(result.scalars().all())

        metrics["completed_chapters"] = completed_count
        return metrics

    @staticmethod
    async def get_prophecy_timeline(db: AsyncSession, user_id: int):
        """Returns a chronological stream of prophecy events and merit snapshots."""
        stmt = select(ProphecyEvent).where(ProphecyEvent.user_id == user_id).order_by(ProphecyEvent.timestamp.desc())
        result = await db.execute(stmt)
        events = result.scalars().all()

        stmt = select(UserMeritSnapshot).where(UserMeritSnapshot.user_id == user_id).order_by(UserMeritSnapshot.timestamp.desc())
        result = await db.execute(stmt)
        snapshots = result.scalars().all()

        # Merge and sort
        timeline = []
        for e in events:
            timeline.append({
                "type": "event",
                "event_type": e.event_type,
                "metadata": e.metadata_json,
                "timestamp": e.timestamp
            })
        for s in snapshots:
            timeline.append({
                "type": "snapshot",
                "accuracy": float(s.accuracy),
                "merit_score": float(s.merit_score),
                "trigger": s.snapshot_trigger,
                "timestamp": s.timestamp
            })

        timeline.sort(key=lambda x: x["timestamp"], reverse=True)
        return timeline
