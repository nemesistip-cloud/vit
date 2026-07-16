import os
import sys
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ---------------------------------------------------------------------------
# Environment bootstrap — must run before any app import so config reads the
# test values rather than system env.  autouse+session keeps this first.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True, scope="session")
def setup_env():
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
    os.environ.setdefault("SESSION_SECRET", "test-session-secret")
    os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_placeholder")
    os.environ.setdefault("PAYSTACK_WEBHOOK_SECRET", "whsec_test_placeholder")
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
    os.environ["AUTH_ENABLED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ["USE_REAL_ML_MODELS"] = "false"
    yield


# ---------------------------------------------------------------------------
# Isolated in-memory database per test
# ---------------------------------------------------------------------------
@pytest.fixture
async def db_session():
    import uuid
    db_url = (
        f"sqlite+aiosqlite:///file:mem_{uuid.uuid4().hex}"
        "?mode=memory&cache=shared&uri=true"
    )
    engine = create_async_engine(db_url, echo=False)

    from app.db.database import Base as AppBase
    from app.core.wallet.models import Base as WalletBase
    from app.modules.sports.models import Base as SportsBase
    from app.modules.blockchain.models import Base as BlockchainBase
    from app.modules.ai.models import Base as AIBase
    import vit_chain.storage.db      # noqa: F401 — registers vit_chain metadata
    import vit_chain.consensus.models  # noqa: F401

    async with engine.begin() as conn:
        for meta in [
            AppBase.metadata,
            WalletBase.metadata,
            SportsBase.metadata,
            BlockchainBase.metadata,
            AIBase.metadata,
        ]:
            try:
                await conn.run_sync(meta.create_all)
            except Exception:
                pass  # table already exists or not applicable for this meta

    import app.db.database as db_mod
    orig_engine = db_mod.engine
    orig_session_factory = db_mod.AsyncSessionLocal

    db_mod.engine = engine
    db_mod.AsyncSessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with db_mod.AsyncSessionLocal() as session:
        # Wire up a fake redis so routes that touch app.state.redis don't crash.
        try:
            from fakeredis.aioredis import FakeRedis
            _fake_redis = FakeRedis()
        except ImportError:
            _fake_redis = None

        import app.core.redis as redis_mod
        redis_mod.redis_client = _fake_redis

        yield session
        await session.close()

    await engine.dispose()
    db_mod.engine = orig_engine
    db_mod.AsyncSessionLocal = orig_session_factory


# ---------------------------------------------------------------------------
# ASGI test client backed by the real FastAPI app
# ---------------------------------------------------------------------------
@pytest.fixture
async def client(db_session):
    from main import app
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Pre-registered user; returns {"Authorization": "Bearer <token>"} headers
# ---------------------------------------------------------------------------
@pytest.fixture
async def auth_headers(client):
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    os.environ["AUTH_ENABLED"] = "true"
    try:
        await client.post("/auth/register", json={
            "email": email,
            "username": f"user_{uuid.uuid4().hex[:8]}",
            "password": "Password123!",
        })
        resp = await client.post("/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        data = resp.json()
        token = data.get("access_token") or data.get("token")
        return {"Authorization": f"Bearer {token}"}
    finally:
        os.environ["AUTH_ENABLED"] = "false"


# ---------------------------------------------------------------------------
# Alias kept for backward-compat with older tests that request setup_database
# ---------------------------------------------------------------------------
@pytest.fixture
async def setup_database(db_session):
    yield
