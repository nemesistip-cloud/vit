import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(autouse=True, scope="session")
def setup_env():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["JWT_SECRET_KEY"] = "test-secret"
    os.environ["AUTH_ENABLED"] = "false"
    yield

@pytest.fixture(autouse=True, scope="session")
def init_db_sync():
    # We use a sync engine just to create the schema for the in-memory DB shared engine
    # Actually main.py uses engine which is already configured.
    # Let's just import and run create_all on the sync side if possible, or use a task.
    # The simplest is to just run a script that does it.
    import asyncio
    from app.db.database import Base, engine
    import app.db.models
    import app.modules.wallet.models
    import app.modules.blockchain.models
    import app.modules.training.models
    import app.modules.ai.models
    import app.data.models
    import app.modules.notifications.models
    import app.modules.marketplace.models
    import app.modules.trust.models
    import app.modules.rewards.models
    import app.modules.bridge.models
    import app.modules.developer.models
    import app.modules.governance.models
    import app.modules.referral.models
    import app.modules.tasks.models
    import app.modules.storage_verification.models
    import app.modules.sports.models

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    yield
