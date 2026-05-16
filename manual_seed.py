
import asyncio
import os
from app.db.database import AsyncSessionLocal
from app.db.models import Match
from app.services.sportsdb_api import backfill_historical_matches, sync_upcoming_fixtures
from sqlalchemy import select, func

async def seed():
    async with AsyncSessionLocal() as db:
        print("📡 Starting manual seed...")
        _months = 1 # Just 1 month for testing speed
        print(f"📡 Backfilling {_months} months of historical matches...")
        hist = await backfill_historical_matches(db, months=_months)
        print(f"✅ Historical: {hist}")

        print(f"📡 Syncing upcoming fixtures...")
        up = await sync_upcoming_fixtures(db, days_ahead=14)
        print(f"✅ Upcoming: {up}")

        count = (await db.execute(select(func.count()).select_from(Match))).scalar()
        print(f"📊 Total matches in DB: {count}")

if __name__ == "__main__":
    asyncio.run(seed())
