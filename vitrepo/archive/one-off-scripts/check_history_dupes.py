import asyncio
from sqlalchemy import select, func
from app.db.database import SessionLocal
from app.db.models import Match, Prediction

async def check():
    async with SessionLocal() as db:
        # Replicate the history query join logic
        # select(Match, Prediction, CLVEntry).join(Prediction, Match.id == Prediction.match_id)

        q = select(Match.id, Prediction.id).join(Prediction, Match.id == Prediction.match_id)
        res = await db.execute(q)
        rows = res.all()
        print(f"Total joined rows: {len(rows)}")

        # Look for duplicate Match IDs in the result
        match_counts = {}
        for mid, pid in rows:
            match_counts[mid] = match_counts.get(mid, 0) + 1

        dupe_matches = {mid: count for mid, count in match_counts.items() if count > 1}
        print(f"Matches with multiple predictions in history: {len(dupe_matches)}")
        for mid, count in list(dupe_matches.items())[:10]:
            print(f"Match ID: {mid}, Prediction Count: {count}")

if __name__ == "__main__":
    asyncio.run(check())
