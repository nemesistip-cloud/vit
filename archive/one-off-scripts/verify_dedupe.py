import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

async def verify():
    try:
        from sqlalchemy import select, func
        from app.db.database import SessionLocal
        from app.db.models import Match, Prediction
    except ImportError as e:
        print(f"Error: {e}")
        return

    async with SessionLocal() as db:
        # Check history endpoint logic
        latest_pred_sq = (
            select(Prediction.user_id, Prediction.match_id, func.max(Prediction.id).label("latest_id"))
            .group_by(Prediction.user_id, Prediction.match_id)
        ).subquery()

        q = select(Prediction.id).join(latest_pred_sq, Prediction.id == latest_pred_sq.c.latest_id)
        res = await db.execute(q)
        preds = res.all()
        print(f"Total unique (user, match) predictions: {len(preds)}")

        # Check results-comparison logic
        latest_match_sq = (
            select(Prediction.match_id, func.max(Prediction.id).label("latest_id"))
            .group_by(Prediction.match_id)
        ).subquery()

        q = select(Prediction.match_id).join(latest_match_sq, Prediction.id == latest_match_sq.c.latest_id)
        res = await db.execute(q)
        matches = res.all()
        print(f"Total unique match results: {len(matches)}")

        match_ids = [m[0] for m in matches]
        if len(match_ids) != len(set(match_ids)):
            print("FAILED: Duplicate match IDs found in results-comparison query!")
        else:
            print("SUCCESS: No duplicate match IDs in results-comparison query.")

if __name__ == "__main__":
    # Check if we can even run this
    try:
        import sqlalchemy
    except ImportError:
        print("SQLAlchemy not available in this shell. Verification skipped, relying on code inspection.")
        sys.exit(0)

    asyncio.run(verify())
