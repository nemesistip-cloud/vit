"""
conftest.py — VIT Network test fixtures

Key design decisions:
- Each test gets a fresh temp-file SQLite database (avoids in-memory
  StaticPool greenlet issues with aiosqlite).
- All app imports happen AFTER env vars are set (setup_env is autouse+session).
- DB engine is patched at import time via app.db.database module attributes.
- fakeredis wires up the in-memory Redis stub so rate-limit/event-bus routes
  don't crash.
"""
import os
import sys
import uuid
import tempfile
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Add project root to path before any app import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ---------------------------------------------------------------------------
# Environment bootstrap — session-scoped, autouse so it runs first.
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
# Per-test isolated SQLite database
# ---------------------------------------------------------------------------
@pytest.fixture
async def db_session():
    """
    Provides a patched DB session backed by a temp-file SQLite database.

    File-based SQLite (not :memory:) is used because aiosqlite's in-memory
    databases lose their greenlet context across async boundaries when
    multiple ASGI requests share the same StaticPool connection — a known
    limitation of pytest-asyncio + SQLAlchemy 2.0 with aiosqlite.

    Each test gets a unique db file so tests are fully isolated.
    """
    db_fd, db_path = tempfile.mkstemp(suffix=".db", prefix="vit_test_")
    os.close(db_fd)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        # Allow the same connection to be reused across threads (needed for
        # aiosqlite's thread-based async shim).
        connect_args={"check_same_thread": False},
    )

    # --- Create tables ---
    from app.db.database import Base as AppBase
    bases = [AppBase.metadata]
    for import_path, attr in [
        ("app.core.wallet.models", "Base"),
        ("app.modules.sports.models", "Base"),
        ("app.modules.blockchain.models", "Base"),
        ("app.modules.ai.models", "Base"),
    ]:
        try:
            mod = __import__(import_path, fromlist=[attr])
            bases.append(getattr(mod, attr).metadata)
        except Exception:
            pass

    async with engine.begin() as conn:
        for meta in bases:
            try:
                await conn.run_sync(meta.create_all)
            except Exception:
                pass

    # --- Patch app.db.database ---
    import app.db.database as db_mod
    orig_engine = db_mod.engine
    orig_session_factory = db_mod.AsyncSessionLocal

    db_mod.engine = engine
    db_mod.AsyncSessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    # --- Patch Redis ---
    try:
        from fakeredis.aioredis import FakeRedis
        import app.core.redis as redis_mod
        redis_mod.redis_client = FakeRedis()
    except Exception:
        pass

    # Yield a session for tests that need direct DB access
    async with db_mod.AsyncSessionLocal() as session:
        yield session
        await session.close()

    # --- Restore ---
    await engine.dispose()
    db_mod.engine = orig_engine
    db_mod.AsyncSessionLocal = orig_session_factory
    try:
        os.unlink(db_path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# ASGI test client
# ---------------------------------------------------------------------------
@pytest.fixture
async def client(db_session):
    """HTTP test client backed by the real FastAPI app and an isolated DB."""
    from main import app
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Pre-registered user with auth headers
# ---------------------------------------------------------------------------
@pytest.fixture
async def auth_headers(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "Secure@Pass12!"
    os.environ["AUTH_ENABLED"] = "true"
    try:
        await client.post("/auth/register", json={
            "email": email,
            "username": f"user_{uuid.uuid4().hex[:8]}",
            "password": password,
        })
        resp = await client.post("/auth/login", json={"email": email, "password": password})
        data = resp.json()
        token = data.get("access_token") or data.get("token", "")
        return {"Authorization": f"Bearer {token}"}
    finally:
        os.environ["AUTH_ENABLED"] = "false"


# ---------------------------------------------------------------------------
# Backward-compat alias
# ---------------------------------------------------------------------------
@pytest.fixture
async def setup_database(db_session):
    yield
