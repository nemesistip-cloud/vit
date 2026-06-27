import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import select, func

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import AsyncSessionLocal
from app.db.models import Match

async def diagnose():
    async with AsyncSessionLocal() as db:
        total = await db.scalar(select(func.count(Match.id)))
        upcoming = await db.scalar(select(func.count(Match.id)).where(Match.kickoff_time > datetime(2026,6,27)))
        print(f"Total Matches: {total}")
        print(f"Upcoming Matches (from June 27): {upcoming}")

        stmt = select(func.date(Match.kickoff_time).label('date'), func.count(Match.id)).where(Match.kickoff_time > datetime(2026,6,27)).group_by('date').order_by('date').limit(10)
        results = await db.execute(stmt)
        print("\nNext 10 Days Distribution:")
        for date, count in results.all():
            print(f"  {date}: {count}")

if __name__ == "__main__":
    asyncio.run(diagnose())
