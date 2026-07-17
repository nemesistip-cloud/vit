import asyncio
import logging
from app.db.database import get_db
from app.services.settlement_service import run_auto_settlement

logger = logging.getLogger(__name__)

async def settlement_worker():
    """Background worker to automatically settle predictions every 15 minutes."""
    logger.info("Starting settlement worker...")
    while True:
        try:
            async for db in get_db():
                result = await run_auto_settlement(db)
                if result.get("settled_matches", 0) > 0:
                    logger.info(f"Auto-settlement complete: {result['settled_matches']} matches, {result['predictions_updated']} predictions")
                break
        except Exception as e:
            logger.error(f"Error in settlement_worker: {e}")

        await asyncio.sleep(900) # 15 minutes

def start_settlement_worker():
    asyncio.create_task(settlement_worker())
