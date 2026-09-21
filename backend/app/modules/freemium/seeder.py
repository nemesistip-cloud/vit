"""Seeder for Freemium module data."""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.freemium.models import IQTestQuestion, OracleMicEpisode

logger = logging.getLogger(__name__)

IQ_QUESTIONS = [
    {
        "q": "A bettor has a 60% win rate on even-money bets (+100 or 2.00 decimal). After 100 bets, what is their expected ROI?",
        "options": ["10%", "20%", "40%", "60%"],
        "correct": 1,
        "explanation": "ROI = (Total Return - Total Stake) / Total Stake. For 100 bets of $1: Stake=$100. Wins=60, Return=60 * $2 = $120. ROI = (120-100)/100 = 20%."
    },
    {
        "q": "Which of these factors is most critical for long-term sports prediction profitability?",
        "options": ["High winning percentage", "Consistently beating the Closing Line (CLV)", "Predicting correct scores", "Parlay size optimization"],
        "correct": 1,
        "explanation": "Closing Line Value (CLV) is the most reliable indicator of long-term success. If you consistently bet at better odds than the final market price, you are likely to be profitable regardless of short-term variance."
    },
    {
        "q": "If Team A has a 75% chance to win, what are the 'Fair Odds' in decimal format?",
        "options": ["1.25", "1.33", "1.50", "1.75"],
        "correct": 1,
        "explanation": "Fair Odds = 1 / Probability. 1 / 0.75 = 1.333..."
    },
    {
        "q": "In a Poisson distribution model for football scores, if the expected goals (Lambda) for a team is 1.0, what is the approximate probability they score exactly 0 goals?",
        "options": ["18%", "25%", "37%", "50%"],
        "correct": 2,
        "explanation": "P(x; L) = (e^-L * L^x) / x!. For x=0, P = e^-1 * 1^0 / 0! = 1/e ≈ 0.3678 or 37%."
    },
    {
        "q": "A 'Market-Maker' sportsbook usually has a lower 'Vig' (margin). If the odds for a two-way market are 1.95 and 1.95, what is the approximate margin?",
        "options": ["1.5%", "2.5%", "5.0%", "7.5%"],
        "correct": 1,
        "explanation": "Margin = (1/1.95 + 1/1.95) - 1 = (0.5128 + 0.5128) - 1 = 0.0256 or 2.56%."
    }
]

ORACLE_EPISODES = [
    {
        "id": str(uuid.uuid4()),
        "title": "The Bayesian Edge: Euro 2024 Tactical Deep Dive",
        "host": "VIT Alpha Node",
        "date": "June 10, 2026",
        "length": "12:45",
        "premium": False,
        "sort_order": 10
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Closing Line Secrets: Why the Last 5 Minutes Matter",
        "host": "Ensemble Lead-7",
        "date": "June 08, 2026",
        "length": "08:20",
        "premium": False,
        "sort_order": 9
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Quantum Markets: Governance and the Future of VIT",
        "host": "Architect-1",
        "date": "June 05, 2026",
        "length": "15:30",
        "premium": True,
        "sort_order": 8
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Scoring the Scorer: Poisson vs Neural Networks",
        "host": "Data-Flow Engine",
        "date": "June 01, 2026",
        "length": "10:15",
        "premium": False,
        "sort_order": 7
    }
]

async def seed_freemium_data(db: AsyncSession):
    """Seed initial data for the Freemium module."""
    # 1. Seed IQ Questions
    q_count_res = await db.execute(select(IQTestQuestion))
    if not q_count_res.scalars().first():
        logger.info("Seeding IQ Test questions...")
        for q_data in IQ_QUESTIONS:
            q = IQTestQuestion(**q_data)
            db.add(q)

    # 2. Seed Oracle Mic Episodes
    e_count_res = await db.execute(select(OracleMicEpisode))
    if not e_count_res.scalars().first():
        logger.info("Seeding Oracle Mic episodes...")
        for e_data in ORACLE_EPISODES:
            e = OracleMicEpisode(**e_data)
            db.add(e)

    await db.commit()
    logger.info("Freemium data seeding complete.")
