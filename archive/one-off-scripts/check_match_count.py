import asyncio
from app.db.database import AsyncSessionLocal
from app.db.models import Match
from sqlalchemy import select, func

async def main():
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count(Match.id)))
        print(f"Total Matches: {count}")

        settled = await db.scalar(select(func.count(Match.id)).where(Match.actual_outcome.isnot(None)))
        print(f"Settled Matches: {settled}")

if __name__ == "__main__":
    asyncio.run(main())
