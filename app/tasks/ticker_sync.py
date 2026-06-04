import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import func, select
from app.db.database import get_db
from app.db.models import User, Match, Prediction
from app.services.firestore_sync import sync_to_firestore

logger = logging.getLogger(__name__)

async def sync_system_ticker():
    """Periodically sync platform stats to Firestore for real-time dashboard."""
    while True:
        try:
            async for db in get_db():
                # Gather stats
                total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
                active_matches = (await db.execute(select(func.count(Match.id)).where(Match.actual_outcome.is_(None)))).scalar() or 0
                total_predictions = (await db.execute(select(func.count(Prediction.id)))).scalar() or 0

                # Accuracy (global)
                # We can calculate this more accurately if needed, but for ticker a simple one is fine

                # Mock price/accuracy for now or fetch from existing services if easy
                data = {
                    "total_users": total_users,
                    "active_matches": active_matches,
                    "total_predictions": total_predictions,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "platform": "VIT Network",
                    "status": "online"
                }

                sync_to_firestore("system", "ticker", data)
                break # Exit the async for loop once we have the db session

        except Exception as e:
            logger.error(f"Error in sync_system_ticker: {e}")

        await asyncio.sleep(60) # Update every minute

def start_ticker_sync():
    asyncio.create_task(sync_system_ticker())
