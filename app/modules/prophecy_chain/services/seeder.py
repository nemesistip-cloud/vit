"""app/modules/prophecy_chain/services/seeder.py — seeder for prophecy chapters."""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.prophecy_chain.models import ProphecyChapter

logger = logging.getLogger(__name__)

async def seed_prophecy_chapters(db: AsyncSession):
    """Seed initial prophecy chapters if table is empty."""
    try:
        count = (await db.execute(select(func.count()).select_from(ProphecyChapter))).scalar()
        if count > 0:
            return 0

        chapters = [
            {
                "title": "The Awakening",
                "description": "Predict 3 consecutive match outcomes correctly.",
                "sequence_order": 1,
                "required_predictions": 3,
                "required_accuracy": 0.60,
                "reward_badge": "Genesis Badge",
                "reward_xp": 100
            },
            {
                "title": "The Seer's Path",
                "description": "Identify 5 positive EV edges in a single matchday.",
                "sequence_order": 2,
                "required_predictions": 8,
                "required_accuracy": 0.65,
                "reward_vit": 50,
                "reward_xp": 250
            },
            {
                "title": "Master of Equilibrium",
                "description": "Predict two 0-0 draws with 80%+ model confidence.",
                "sequence_order": 3,
                "required_predictions": 15,
                "required_accuracy": 0.70,
                "reward_badge": "Stalemate NFT",
                "reward_xp": 500
            },
            {
                "title": "The Oracle Ascends",
                "description": "Maintain a 65% win rate over 100 bets.",
                "sequence_order": 4,
                "required_predictions": 100,
                "required_accuracy": 0.65,
                "reward_badge": "Oracle Tier Status",
                "reward_xp": 1000
            }
        ]

        for ch_data in chapters:
            db.add(ProphecyChapter(**ch_data))

        await db.commit()
        logger.info(f"Seeded {len(chapters)} prophecy chapters")
        return len(chapters)
    except Exception as e:
        logger.error(f"Failed to seed prophecy chapters: {e}")
        await db.rollback()
        return 0
