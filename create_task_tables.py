#!/usr/bin/env python3
"""Create task system tables manually."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import Base, engine
from app.modules.tasks.models import TaskCategory, Task, UserTaskCompletion


async def create_tables():
    """Create the task system tables."""
    try:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("Task system tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_tables())