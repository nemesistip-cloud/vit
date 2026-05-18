import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.rewards.service import RewardService
from app.modules.prophecy_chain.models import ProphecyChapter
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RewardEngine:
    """Handles issuance of non-financial and eventually financial rewards."""

    @staticmethod
    async def issue_chapter_rewards(db: AsyncSession, user_id: int, chapter: ProphecyChapter):
        """Dispatches rewards based on chapter config."""
        config = chapter.reward_config
        logger.info(f"Issuing rewards for chapter {chapter.title} to user {user_id}: {config}")

        # 1. Issue XP (Leveraging existing RewardService if available, or direct DB update)
        xp_amount = config.get("xp", 0)
        if xp_amount > 0:
            try:
                # Assuming User model has total_xp
                from app.db.models import User
                from sqlalchemy import update
                await db.execute(update(User).where(User.id == user_id).values(total_xp=User.total_xp + xp_amount))
            except Exception as e:
                logger.warning(f"Failed to issue XP: {e}")

        # 2. Issue Badges/Titles (Non-financial Phase 1)
        badge = config.get("badge")
        title = config.get("title")
        if badge or title:
            # For now, record as a notification or metadata on user
            # In Phase 2, this would update a 'user_achievements' table
            await RewardEngine._record_achievement(db, user_id, badge, title)

        # 3. Access Rights (e.g., unlock premium models)
        access_unlocks = config.get("access_unlocks", [])
        if access_unlocks:
            await RewardEngine._grant_access(db, user_id, access_unlocks)

        # 4. Economic Rewards (Phase 3 - Placeholder)
        vit_amount = config.get("vit", 0)
        if vit_amount > 0:
            logger.info(f"Phase 3: {vit_amount} VIT reward queued for user {user_id}")
            # await WalletService.deposit(user_id, vit_amount, "prophecy_reward")

    @staticmethod
    async def _record_achievement(db: AsyncSession, user_id: int, badge: str, title: str):
        # Implementation for recording achievements
        pass

    @staticmethod
    async def _grant_access(db: AsyncSession, user_id: int, unlocks: list):
        # Implementation for granting feature access
        pass
