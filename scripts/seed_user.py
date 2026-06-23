import asyncio
import bcrypt as _bcrypt
from app.db.database import AsyncSessionLocal
from app.db.models import User

async def seed_user():
    async with AsyncSessionLocal() as db:
        hashed = _bcrypt.hashpw("password123".encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hashed,
            role="pro",
            is_active=True
        )
        db.add(user)
        await db.commit()
        print("Test user created: test@example.com / password123")

if __name__ == "__main__":
    asyncio.run(seed_user())
