import asyncio
from sqlalchemy import select, func
from app.db.database import SessionLocal
from app.db.models import Match, Prediction

async def check():
    async with SessionLocal() as db:
        # Check for matches with same fingerprint
        q = select(Match.fingerprint, func.count(Match.id)).group_by(Match.fingerprint).having(func.count(Match.id) > 1)
        res = await db.execute(q)
        dupe_matches = res.all()
        print(f"Duplicate match fingerprints: {len(dupe_matches)}")
        for f, c in dupe_matches:
            print(f"Fingerprint: {f}, Count: {c}")

        # Check for matches with multiple predictions
        q = select(Prediction.match_id, func.count(Prediction.id)).group_by(Prediction.match_id).having(func.count(Prediction.id) > 1)
        res = await db.execute(q)
        multi_preds = res.all()
        print(f"\nMatches with multiple predictions: {len(multi_preds)}")
        for mid, c in multi_preds[:10]:
            print(f"Match ID: {mid}, Prediction Count: {c}")

if __name__ == "__main__":
    asyncio.run(check())
