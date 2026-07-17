#!/usr/bin/env python3
"""
Standalone DB initialisation — runs BEFORE uvicorn on every deploy.

1. Imports every SQLAlchemy model so Base.metadata is fully populated.
2. Calls Base.metadata.create_all() with checkfirst=True — safe to run
   repeatedly; only creates tables that don't exist yet.

This is a safety-net for cases where alembic fails (divergent heads,
bad migration, fresh DB) so the ORM can still query a working schema.
Exits 0 always — failures are logged but never block startup.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="[init_db] %(message)s")
log = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if "postgres" not in DATABASE_URL:
    log.info("No Postgres DATABASE_URL — skipping init_db.")
    sys.exit(0)

# Normalise URL to psycopg2/psycopg form (synchronous).
sync_url = DATABASE_URL
for old, new in [
    ("postgresql+asyncpg://", "postgresql://"),
    ("postgres+asyncpg://",   "postgresql://"),
    ("postgres://",            "postgresql://"),
]:
    if sync_url.startswith(old):
        sync_url = new + sync_url[len(old):]
        break

try:
    import sqlalchemy as sa
    from sqlalchemy import create_engine
except ImportError:
    log.error("sqlalchemy not installed — skipping init_db.")
    sys.exit(0)

try:
    # ── 1. Import Base ──────────────────────────────────────────────────────
    from app.db.database import Base

    # ── 2. Register ALL models with Base (mirrors alembic/env.py) ──────────
    import app.db.models                         # noqa: F401  User, AuditLog, Match, …
    import app.modules.wallet.models             # noqa: F401
    import app.modules.blockchain.models         # noqa: F401
    import app.modules.notifications.models      # noqa: F401
    import app.modules.marketplace.models        # noqa: F401
    import app.modules.tasks.models              # noqa: F401
    import app.modules.trust.models              # noqa: F401
    import app.modules.bridge.models             # noqa: F401
    import app.modules.developer.models          # noqa: F401
    import app.modules.governance.models         # noqa: F401
    import app.modules.rewards.models            # noqa: F401
    import app.modules.identity.models           # noqa: F401
    # Best-effort imports — skip silently if the module has import issues
    for _mod in [
        "app.modules.ai.models",
        "app.modules.freemium.models",
        "app.data.models",
        "app.modules.training.models",
    ]:
        try:
            __import__(_mod)
        except Exception as _e:
            log.warning("Skipping %s: %s", _mod, _e)

    log.info("All models imported — %d tables in metadata.",
             len(Base.metadata.tables))

    # ── 3. create_all ───────────────────────────────────────────────────────
    engine = create_engine(sync_url, connect_args={"connect_timeout": 10})
    with engine.begin() as conn:
        Base.metadata.create_all(conn, checkfirst=True)
    engine.dispose()
    log.info("create_all() complete — all tables verified/created.")

except Exception as exc:
    log.error("init_db failed (non-fatal): %s", exc)
    sys.exit(0)  # never block startup
