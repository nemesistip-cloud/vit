import os
import sys
import uuid
import asyncio
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("VIT_DATABASE_URL", "sqlite+aiosqlite:///./vit.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-pytest-only")
os.environ.setdefault("SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FOOTBALL_DATA_API_KEY", "")
os.environ.setdefault("THE_ODDS_API_KEY", "")
os.environ.setdefault("ODDS_API_KEY", "")
os.environ.setdefault("USE_REAL_ML_MODELS", "false")
os.environ.setdefault("BLOCKCHAIN_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Ensure all database tables are created before running tests."""
    from app.db.database import Base, engine, AsyncSessionLocal

    # Force clean DB for tests if it's SQLite
    db_url = os.environ.get("VIT_DATABASE_URL", "")
    if "sqlite" in db_url:
        db_path = db_url.split("///")[-1]
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except (PermissionError, FileNotFoundError):
                pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run seeding logic
    from app.modules.wallet.models import PlatformConfig
    from app.db.models import SubscriptionPlan, User
    from app.modules.tasks.models import TaskCategory, Task
    from app.core.seeding import PLATFORM_CONFIG_DEFAULTS, SUBSCRIPTION_PLANS, TASK_CATEGORIES, TASK_DEFINITIONS
    from app.auth.jwt_utils import hash_password

    async with AsyncSessionLocal() as db:
        # Create a default admin user for task creation
        admin = User(
            email="admin@vit.network",
            username="admin",
            hashed_password=hash_password("AdminPass123!"),
            role="admin",
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        await db.flush()
        admin_id = admin.id

        # Platform Config
        for key, value, desc in PLATFORM_CONFIG_DEFAULTS:
            db.add(PlatformConfig(key=key, value=value, description=desc))

        # Subscription Plans
        for p in SUBSCRIPTION_PLANS:
            db.add(SubscriptionPlan(
                name=p["name"],
                display_name=p["display_name"],
                price_monthly=p["price_monthly"],
                price_yearly=p["price_yearly"],
                prediction_limit=p["prediction_limit"],
                features=p["features"],
                is_active=True,
            ))

        # Task Categories and Definitions
        cat_map = {}
        for cat in TASK_CATEGORIES:
            c = TaskCategory(**cat, is_active=True)
            db.add(c)
            await db.flush()
            cat_map[cat["name"]] = c.id

        for td in TASK_DEFINITIONS:
            db.add(Task(
                category_id=cat_map[td["category_name"]],
                title=td["title"],
                description=td["description"],
                short_description=td.get("short_description"),
                task_type=td["task_type"],
                required_count=td.get("required_count", 1),
                max_completions=td.get("max_completions", 1),
                vit_reward=td.get("vit_reward", 0),
                xp_reward=td.get("xp_reward", 0),
                created_by=admin_id
            ))

        await db.commit()

    yield


@pytest.fixture
def base_url():
    return "http://testserver"


@pytest.fixture
async def client(base_url):
    from main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=base_url) as ac:
        yield ac


@pytest.fixture
def unique_email():
    return f"test_{uuid.uuid4().hex[:8]}@vit.network"


@pytest.fixture
async def registered_user(client, unique_email):
    """Register a fresh user and return their credentials + token response."""
    payload = {
        "email": unique_email,
        "username": f"tester_{uuid.uuid4().hex[:6]}",
        "password": "TestPass123!",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201, f"Registration failed: {response.text}"
    data = response.json()
    return {
        "email": unique_email,
        "password": payload["password"],
        "username": payload["username"],
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user_id": data["user_id"],
        "role": data["role"],
    }


@pytest.fixture
def auth_headers(registered_user):
    """Bearer auth headers built from a freshly registered user."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}
