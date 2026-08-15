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
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

# Add project root to path before any app import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Test environment defaults needed before importing app modules at collection time.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_placeholder")
os.environ.setdefault("PAYSTACK_WEBHOOK_SECRET", "whsec_test_placeholder")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("USE_REAL_ML_MODELS", "false")

# Alembic config helpers

def _alembic_config() -> str:
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    return str(config_path)


def _bootstrap_sqlite_schema(database_url: str) -> None:
    """Populate a fresh SQLite test DB with the current ORM schema."""
    from sqlalchemy import create_engine
    from app.db.database import Base

    # Import all models that contribute to the canonical metadata.
    import app.db.models  # noqa: F401
    import app.modules.wallet.models  # noqa: F401
    import app.modules.blockchain.models  # noqa: F401
    import app.modules.notifications.models  # noqa: F401
    import app.modules.marketplace.models  # noqa: F401
    import app.modules.tasks.models  # noqa: F401
    import app.modules.trust.models  # noqa: F401
    import app.modules.bridge.models  # noqa: F401
    import app.modules.developer.models  # noqa: F401
    import app.modules.governance.models  # noqa: F401
    import app.modules.rewards.models  # noqa: F401

    _OPTIONAL_MODELS = [
        "app.modules.training.models",
        "app.modules.ai.models",
        "app.data.models",
        "app.modules.freemium.models",
    ]
    for _mod in _OPTIONAL_MODELS:
        try:
            __import__(_mod)
        except Exception:
            pass

    sync_url = database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        Base.metadata.create_all(conn, checkfirst=True)
    engine.dispose()


def run_alembic_migrations(database_url: str) -> None:
    import subprocess
    import shutil
    from pathlib import Path

    alembic_path = shutil.which("alembic")
    if not alembic_path:
        raise RuntimeError("Alembic CLI not found in PATH")

    alembic_config = _alembic_config()
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)

    repo_root = Path(__file__).resolve().parents[1]
    if database_url.startswith("sqlite+aiosqlite://"):
        _bootstrap_sqlite_schema(database_url)
        cmd = [alembic_path, "-c", alembic_config, "stamp", "heads"]
    else:
        cmd = [alembic_path, "-c", alembic_config, "upgrade", "heads"]

    subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

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
    # Ensure a session-level SQLite file DB has a schema before importing main.
    # This uses Alembic so the test DB matches the production migration path.
    try:
        from importlib import import_module

        raw = os.environ.get("DATABASE_URL", "")
        if raw and "sqlite" in raw:
            # Alembic requires DATABASE_URL to be set for env.py.
            run_alembic_migrations(raw)
    except Exception:
        pass

    yield


# ---------------------------------------------------------------------------
# Per-test isolated SQLite database
# ---------------------------------------------------------------------------
@pytest.fixture
async def db_engine():
    """Patch the app DB engine to a fresh temp-file SQLite database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db", prefix="vit_test_")
    os.close(db_fd)
    print(f"[conftest] using temp db: {db_path}")

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        future=True,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )

    # --- Create tables by applying Alembic migrations to the temp DB.
    run_alembic_migrations(f"sqlite+aiosqlite:///{db_path}")

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

    yield engine

    # --- Restore ---
    await engine.dispose()
    db_mod.engine = orig_engine
    db_mod.AsyncSessionLocal = orig_session_factory
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
async def db_session(db_engine):
    """Provides a fresh session from the patched test DB engine."""
    import app.db.database as db_mod
    async with db_mod.AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# ASGI test client
# ---------------------------------------------------------------------------
@pytest.fixture
async def client(db_engine):
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


@pytest.fixture(autouse=True)
def reset_module_registry():
    from app.core.registry.manager import ModuleRegistry
    ModuleRegistry().clear()
    yield
    ModuleRegistry().clear()
