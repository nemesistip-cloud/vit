import os
import sys
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(autouse=True, scope="session")
def setup_env():
    os.environ["JWT_SECRET_KEY"] = "test-secret"
    os.environ["ENVIRONMENT"] = "testing"
    yield

@pytest.fixture
async def db_session():
    # Use a unique memory database name to avoid any collision
    import uuid
    db_url = f"sqlite+aiosqlite:///file:{uuid.uuid4()}?mode=memory&cache=shared"
    engine = create_async_engine(db_url, echo=False)

    from app.core.wallet.models import Base as WalletBase
    async with engine.begin() as conn:
        await conn.run_sync(WalletBase.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        from app.core.redis import require_redis
        class MockApp:
            state = type('State', (), {'redis': None})
        await require_redis(MockApp())

        yield session
        await session.close()
    await engine.dispose()
