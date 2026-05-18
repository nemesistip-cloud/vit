import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.prophecy_chain.models import ProphecyChapter, ChapterTier

logger = logging.getLogger(__name__)

CANONICAL_CHAPTERS = [
    {
        "unlock_order": 0,
        "tier": ChapterTier.INITIATE,
        "title": "The Awakening",
        "description": "Every signal begins as noise. The Initiate learns to distinguish emotion from probability.",
        "lore": "You have entered the VIT network. Your first task is to prove you can act with discipline, submitting your first predictions into the collective intelligence. Noise is a comfort; signal is a responsibility.",
        "requirements": {
            "qualified_predictions": 2,
            "qualified_accuracy": 0.35
        },
        "reward_config": {
            "vit": 10,
            "xp": 50,
            "badge": "Initiate Badge",
            "title": "Initiate"
        }
    },
    {
        "unlock_order": 1,
        "tier": ChapterTier.PATTERN_RECOGNITION,
        "title": "Pattern Recognition",
        "description": "The market repeats itself through human behavior. Patterns emerge to disciplined observers.",
        "lore": "Consistency is the first step toward mastery. You must demonstrate that your early success was not mere chance. The market has a memory, and so do we.",
        "requirements": {
            "qualified_predictions": 25,
            "qualified_accuracy": 0.55,
            "unique_leagues": 2
        },
        "reward_config": {
            "vit": 50,
            "xp": 200,
            "badge": "Pattern Seeker",
            "title": "Pattern Seeker"
        }
    },
    {
        "unlock_order": 2,
        "tier": ChapterTier.SIGNAL_HUNTER,
        "title": "Signal Hunter",
        "description": "Most follow outcomes. The Hunter studies inefficiencies.",
        "lore": "True value is found where the crowd fears to tread. Detect the signal, ignore the noise. You are no longer chasing winning bets; you are chasing mispriced reality.",
        "requirements": {
            "qualified_predictions": 50,
            "qualified_accuracy": 0.58,
            "unique_leagues": 3
        },
        "reward_config": {
            "vit": 100,
            "xp": 500,
            "badge": "Signal Hunter",
            "title": "Signal Hunter"
        }
    },
    {
        "unlock_order": 3,
        "tier": ChapterTier.RISK_ARCHITECT,
        "title": "Risk Architect",
        "description": "True foresight is measured not by victory, but by survival through uncertainty.",
        "lore": "The Architect understands that luck is a temporary state, but discipline is an infinite game. Manage your volatility as strictly as your predictions.",
        "requirements": {
            "qualified_predictions": 100,
            "qualified_accuracy": 0.60,
            "unique_leagues": 5
        },
        "reward_config": {
            "vit": 250,
            "xp": 1000,
            "badge": "Risk Architect",
            "title": "Architect"
        }
    },
    {
        "unlock_order": 4,
        "tier": ChapterTier.ORACLE,
        "title": "The Oracle Ascends",
        "description": "The Oracle does not chase certainty. They calibrate probability against consequence.",
        "lore": "You have reached the upper echelons of the network. Your foresight is now a recognized asset to the intelligence civilization. Prediction is no longer instinct; it is calibrated intelligence forged through consequence.",
        "requirements": {
            "qualified_predictions": 200,
            "qualified_accuracy": 0.62,
            "best_streak": 5,
            "unique_leagues": 8
        },
        "reward_config": {
            "vit": 500,
            "xp": 2000,
            "badge": "Oracle Tier",
            "title": "Oracle"
        }
    },
    {
        "unlock_order": 5,
        "tier": ChapterTier.VALIDATOR,
        "title": "The High Validator",
        "description": "At the highest level, intelligence no longer competes. It safeguards the integrity of the system itself.",
        "lore": "The final evolution. You do not just predict the future; you verify the collective foresight of the civilization. Trust is the ultimate currency, and you are its guardian.",
        "requirements": {
            "qualified_predictions": 500,
            "qualified_accuracy": 0.65,
            "best_streak": 8,
            "unique_leagues": 12
        },
        "reward_config": {
            "vit": 1000,
            "xp": 5000,
            "badge": "Validator Badge",
            "title": "High Validator",
            "access_unlocks": ["governance_validator", "premium_analytics"]
        }
    }
]

async def seed_prophecy_chapters(db: AsyncSession):
    """Idempotent seeding of canonical prophecy chapters."""
    logger.info("Seeding prophecy chapters...")
    count = 0
    for ch_data in CANONICAL_CHAPTERS:
        stmt = select(ProphecyChapter).where(ProphecyChapter.title == ch_data["title"])
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            chapter = ProphecyChapter(**ch_data)
            db.add(chapter)
            count += 1
        else:
            # Update existing lore/description/requirements to match the new refined versions
            existing.description = ch_data["description"]
            existing.lore = ch_data["lore"]
            existing.requirements = ch_data["requirements"]
            existing.reward_config = ch_data["reward_config"]
            existing.unlock_order = ch_data["unlock_order"]
            existing.tier = ch_data["tier"]

    await db.commit()
    return count
