#!/usr/bin/env python3
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    from app.db.database import AsyncSessionLocal
    from app.services.prediction_seeder import seed_upcoming_predictions, seed_predictions_for_historical
    async with AsyncSessionLocal() as db:
        res_up = await seed_upcoming_predictions(db)
        print(f"[seed_predictions] Upcoming: {res_up}")
        res_hist = await seed_predictions_for_historical(db)
        print(f"[seed_predictions] Historical: {res_hist}")

if __name__ == "__main__":
    asyncio.run(main())
