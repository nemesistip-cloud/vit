import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import AsyncSessionLocal
from app.services.sportsdb_api import backfill_historical_matches
from app.config import BOOTSTRAP_MATCH_MONTHS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sportsdb-backfill")

async def run_backfill():
    """Manual trigger for TheSportsDB historical backfill."""
    # Production logic uses config value
    months = BOOTSTRAP_MATCH_MONTHS
    logger.info(f"Starting TheSportsDB backfill for last {months} month(s)...")

    async with AsyncSessionLocal() as db:
        try:
            result = await backfill_historical_matches(db, months=months)
            logger.info(
                f"Backfill complete: "
                f"Inserted: {result['inserted']}, "
                f"Updated: {result['updated']}, "
                f"Skipped: {result['skipped']}, "
                f"Total Fetched: {result['total_fetched']}"
            )
        except Exception as e:
            logger.error(f"Backfill failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_backfill())
