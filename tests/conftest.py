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
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["AUTH_ENABLED"] = "false"
    yield

@pytest.fixture
async def db_session():
    import uuid
    # Standard isolated in-memory DB for tests
    db_url = f"sqlite+aiosqlite:///file:mem_{uuid.uuid4().hex}?mode=memory&cache=shared"
    engine = create_async_engine(db_url, echo=False)

    from app.db.database import Base as AppBase
    from app.core.wallet.models import Base as WalletBase
    from app.modules.sports.models import Base as SportsBase
    from app.modules.blockchain.models import Base as BlockchainBase
    from app.modules.ai.models import Base as AIBase
    import vit_chain.storage.db # noqa: F401
    import vit_chain.consensus.models # noqa: F401

    async with engine.begin() as conn:
        all_metas = [AppBase.metadata, WalletBase.metadata, SportsBase.metadata, BlockchainBase.metadata, AIBase.metadata]
        for meta in all_metas:
            try:
                await conn.run_sync(meta.create_all)
            except Exception:
                pass

    import app.db.database as db_mod
    orig_engine = db_mod.engine
    orig_AsyncSessionLocal = db_mod.AsyncSessionLocal

    db_mod.engine = engine
    db_mod.AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with db_mod.AsyncSessionLocal() as session:
        from app.core.redis import require_redis
        class MockApp:
            state = type('State', (), {'redis': None})
        await require_redis(MockApp())
        yield session
        await session.close()

    await engine.dispose()
    db_mod.engine = orig_engine
    db_mod.AsyncSessionLocal = orig_AsyncSessionLocal

@pytest.fixture
async def client(db_session):
    from main import app
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac

@pytest.fixture
async def auth_headers(client):
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    os.environ["AUTH_ENABLED"] = "true"
    await client.post("/auth/register", json={
        "email": email,
        "username": f"user_{uuid.uuid4().hex[:8]}",
        "password": "Password123!",
    })
    resp = await client.post("/auth/login", json={
        "email": email,
        "password": "Password123!",
    })
    os.environ["AUTH_ENABLED"] = "false"
    data = resp.json()
    token = data.get("access_token")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def setup_database(db_session):
    yield
