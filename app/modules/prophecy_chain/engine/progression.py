import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.modules.prophecy_chain.models import ProphecyChapter, UserProphecyProgress, ProphecyEvent, UserMeritSnapshot
from app.modules.prophecy_chain.engine.rewards import RewardEngine
from app.db.models import User, Prediction, Match
from app.modules.merit.models import MeritScore
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Anti-Exploit Constants
MIN_QUALIFIED_ODDS = 1.35
MAX_QUALIFIED_PREDICTIONS_PER_DAY = 15

class ProgressionEngine:
    """Evaluates user progress against prophecy chapter requirements with anti-exploit rules."""

    @staticmethod
    async def evaluate_user_progress(db: AsyncSession, user_id: int, trigger: str = "system"):
        """Main entry point for re-evaluating all active chapters for a user."""
        logger.info(f"Evaluating prophecy progress for user {user_id} triggered by {trigger}")

        # 1. Get all active chapters
        stmt = select(ProphecyChapter).where(ProphecyChapter.is_active == True).order_by(ProphecyChapter.unlock_order)
        result = await db.execute(stmt)
        chapters = result.scalars().all()

        # 2. Get user current progress
        stmt = select(UserProphecyProgress).where(UserProphecyProgress.user_id == user_id)
        result = await db.execute(stmt)
        progress_map = {p.chapter_id: p for p in result.scalars().all()}

        # 3. Get user metrics (with anti-exploit logic)
        metrics = await ProgressionEngine._get_user_metrics(db, user_id)

        for chapter in chapters:
            user_progress = progress_map.get(chapter.id)

            # If no progress record, create one
            if not user_progress:
                user_progress = UserProphecyProgress(
                    user_id=user_id,
                    chapter_id=chapter.id,
                    unlocked=(chapter.unlock_order == 0) # First chapter unlocked by default
                )
                db.add(user_progress)
                await db.flush()

            # If already completed, skip
            if user_progress.is_completed:
                continue

            # Check if unlocked (if not first chapter, check if previous is completed)
            if not user_progress.unlocked and chapter.unlock_order > 0:
                prev_chapter = next((c for c in chapters if c.unlock_order == chapter.unlock_order - 1), None)
                if prev_chapter:
                    prev_progress = progress_map.get(prev_chapter.id)
                    if prev_progress and prev_progress.is_completed:
                        user_progress.unlocked = True
                        user_progress.unlocked_at = datetime.now(timezone.utc)
                        await ProgressionEngine._record_event(db, user_id, "chapter_unlocked", {"chapter_id": chapter.id, "title": chapter.title})

            # If still locked, skip completion check
            if not user_progress.unlocked:
                continue

            # Evaluate completion requirements
            completed, current_progress = await ProgressionEngine._check_requirements(chapter.requirements, metrics)
            user_progress.progress_data = current_progress

            if completed:
                user_progress.is_completed = True
                user_progress.completed_at = datetime.now(timezone.utc)

                # Take immutable snapshot upon completion
                await ProgressionEngine._take_merit_snapshot(db, user_id, metrics, f"chapter_completed:{chapter.title}")

                await ProgressionEngine._record_event(db, user_id, "chapter_completed", {"chapter_id": chapter.id, "title": chapter.title})

                # Trigger rewards
                try:
                    await RewardEngine.issue_chapter_rewards(db, user_id, chapter)
                except Exception as _re_e:
                    logger.error(f"Reward issuance failed for chapter {chapter.title}: {_re_e}")

        await db.commit()

    @staticmethod
    async def _get_user_metrics(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Gathers all necessary telemetry for a user with Anti-Exploit filters."""

        # Fetch merit score
        stmt = select(MeritScore).where(MeritScore.user_id == user_id)
        result = await db.execute(stmt)
        merit = result.scalar_one_or_none()

        # Fetch ALL settled predictions for this user
        stmt = (
            select(Prediction, Match.league)
            .join(Match, Prediction.match_id == Match.id)
            .where(Prediction.user_id == user_id, Prediction.was_correct.isnot(None))
        )
        result = await db.execute(stmt)
        rows = result.all()

        # Filter for "Qualified" predictions (Anti-Exploit: Odds >= 1.35)
        qualified_preds = []
        unique_leagues: Set[str] = set()
        total_odds = 0.0

        for pred, league in rows:
            odds = pred.entry_odds or 0.0
            if odds >= MIN_QUALIFIED_ODDS:
                qualified_preds.append(pred)
                unique_leagues.add(league)
                total_odds += odds

        qualified_total = len(qualified_preds)
        qualified_wins = sum(1 for p in qualified_preds if p.was_correct)
        qualified_accuracy = (qualified_wins / qualified_total) if qualified_total > 0 else 0
        avg_odds = (total_odds / qualified_total) if qualified_total > 0 else 0

        # Anti-Exploit: Daily Volume Check
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        stmt = select(func.count(Prediction.id)).where(
            Prediction.user_id == user_id,
            Prediction.timestamp >= one_day_ago,
            Prediction.entry_odds >= MIN_QUALIFIED_ODDS
        )
        daily_vol_res = await db.execute(stmt)
        daily_qualified_volume = daily_vol_res.scalar() or 0

        # Weight adjustments based on daily volume (penalty if spamming)
        volume_multiplier = 1.0
        if daily_qualified_volume > MAX_QUALIFIED_PREDICTIONS_PER_DAY:
            volume_multiplier = max(0.1, 1.0 - (daily_qualified_volume - MAX_QUALIFIED_PREDICTIONS_PER_DAY) * 0.05)

        # Streak
        stmt = select(User.current_streak, User.best_streak).where(User.id == user_id)
        result = await db.execute(stmt)
        user_row = result.fetchone()

        return {
            "merit_score": float(merit.score) if merit else 0,
            "trust_score": float(merit.score / 1000) if merit else 0, # Placeholder calc
            "qualified_predictions": qualified_total,
            "qualified_accuracy": qualified_accuracy,
            "unique_leagues": len(unique_leagues),
            "avg_odds": avg_odds,
            "current_streak": user_row[0] if user_row else 0,
            "best_streak": user_row[1] if user_row else 0,
            "daily_volume_penalty": 1.0 - volume_multiplier
        }

    @staticmethod
    async def _check_requirements(requirements: Dict[str, Any], metrics: Dict[str, Any]) -> (bool, Dict[str, Any]):
        """Compares requirements vs metrics."""
        completed = True
        progress_data = {}

        for req_key, req_val in requirements.items():
            metric_val = metrics.get(req_key, 0)
            progress_data[req_key] = metric_val

            if metric_val < req_val:
                completed = False

        return completed, progress_data

    @staticmethod
    async def _take_merit_snapshot(db: AsyncSession, user_id: int, metrics: Dict[str, Any], trigger: str):
        snapshot = UserMeritSnapshot(
            user_id=user_id,
            accuracy=metrics["qualified_accuracy"],
            qualified_predictions=metrics["qualified_predictions"],
            avg_odds=metrics["avg_odds"],
            merit_score=metrics["merit_score"],
            trust_score=metrics["trust_score"],
            unique_leagues=metrics["unique_leagues"],
            snapshot_trigger=trigger
        )
        db.add(snapshot)

    @staticmethod
    async def _record_event(db: AsyncSession, user_id: int, event_type: str, metadata: Dict[str, Any]):
        event = ProphecyEvent(
            user_id=user_id,
            event_type=event_type,
            metadata_json=metadata
        )
        db.add(event)
