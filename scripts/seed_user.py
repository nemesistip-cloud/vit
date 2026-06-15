import asyncio
from app.db.database import AsyncSessionLocal
from app.db.models import User
from passlib.hash import bcrypt

async def seed_user():
    async with AsyncSessionLocal() as db:
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=bcrypt.hash("password123"),
            role="pro",
            is_active=True
        )
        db.add(user)
        await db.commit()
        print("Test user created.")

if __name__ == "__main__":
    asyncio.run(seed_user())
