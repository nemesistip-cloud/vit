#!/usr/bin/env python3
"""
Clean up test predictions and related data.
Run: python scripts/cleanup_predictions.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import async_session_factory
from sqlalchemy import text

TABLES_TO_CLEAR = [
    "predictions",
    "clv_entries", 
    "prediction_history",
    "ai_prediction_audits",
    "decision_logs",
]

async def cleanup():
    async with async_session_factory() as session:
        print("🔍 Current counts:")
        for table in TABLES_TO_CLEAR:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {table}: {count}")
        
        print("\n🧹 Cleaning up...")
        for table in TABLES_TO_CLEAR:
            await session.execute(text(f"DELETE FROM {table}"))
            print(f"  ✅ Cleared {table}")
        
        # Reset SQLite sequences if using SQLite
        db_url = os.getenv("DATABASE_URL", "")
        if "sqlite" in db_url:
            await session.execute(text("DELETE FROM sqlite_sequence WHERE name IN :tables"), 
                                  {"tables": tuple(TABLES_TO_CLEAR)})
            print("  ✅ Reset auto-increment counters")
        
        await session.commit()
        
        print("\n📊 New counts:")
        for table in TABLES_TO_CLEAR:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {table}: {count}")
        
        print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(cleanup())