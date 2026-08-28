# alembic/env.py
import sys
import os
from logging.config import fileConfig
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from alembic import context

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# ── Model imports ─────────────────────────────────────────────────────────────
# Required models (must succeed — these define the core schema).
from app.db.models import Base  # noqa: E402
import app.db.models            # noqa: E402
import app.modules.wallet.models       # noqa: E402
import app.modules.blockchain.models   # noqa: E402
import app.modules.notifications.models  # noqa: E402
import app.modules.marketplace.models  # noqa: E402
import app.modules.tasks.models        # noqa: E402
import app.modules.trust.models        # noqa: E402
import app.modules.bridge.models       # noqa: E402
import app.modules.developer.models    # noqa: E402
import app.modules.governance.models   # noqa: E402
import app.modules.rewards.models      # noqa: E402

# Optional models — some may depend on heavy ML libraries or have conditional
# imports.  Wrap each in try/except so a single bad import doesn't crash Alembic.
_OPTIONAL_MODELS = [
    "app.modules.training.models",
    "app.modules.ai.models",
    "app.data.models",
    "app.modules.freemium.models",
    "app.modules.identity.models",
]
for _mod in _OPTIONAL_MODELS:
    try:
        __import__(_mod)
    except Exception as _e:
        print(f"[alembic/env.py] WARNING: could not import {_mod}: {_e}", file=sys.stderr)

# ── Database URL ──────────────────────────────────────────────────────────────
# Read from the raw environment variable so we can control sslmode ourselves.
# app.db.database converts to asyncpg AND strips sslmode; we need the original
# URL to build a psycopg2-compatible sync URL with proper SSL settings.
_raw_db_url: str = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./vit.db")

# Import the asyncpg version just to confirm we parsed config correctly;
# Alembic uses its own sync engine built below.
try:
    from app.db.database import DATABASE_URL as _ASYNC_URL  # noqa: F401
except Exception:
    _ASYNC_URL = _raw_db_url


def _make_sync_url(url: str) -> str:
    """Convert any postgres URL variant to a psycopg2-compatible sync URL.

    Also ensures sslmode is set appropriately:
      - localhost / helium (Replit internal): sslmode=disable
      - all other hosts (Render, AWS, etc.): sslmode=require
    """
    # Strip asyncpg/aiosqlite driver suffixes → plain scheme
    for old, new in [
        ("postgresql+asyncpg://", "postgresql://"),
        ("postgres+asyncpg://",   "postgresql://"),
        ("sqlite+aiosqlite://",   "sqlite://"),
        ("postgres://",           "postgresql://"),
    ]:
        if url.startswith(old):
            url = new + url[len(old):]
            break

    if not url.startswith("postgresql"):
        return url  # SQLite or unknown — return as-is

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # Determine SSL requirement based on host
    host = parsed.hostname or ""
    local_hosts = {"localhost", "127.0.0.1", "helium", ""}
    if host in local_hosts:
        query.setdefault("sslmode", "disable")
    else:
        # Render managed Postgres and most cloud providers require SSL.
        query.setdefault("sslmode", "require")

    # Convert scheme to psycopg2
    scheme = parsed.scheme.replace("+asyncpg", "+psycopg2")
    if scheme in ("postgresql", "postgres"):
        scheme = "postgresql+psycopg2"
    elif "+psycopg2" not in scheme:
        scheme = "postgresql+psycopg2"

    return urlunparse(parsed._replace(scheme=scheme, query=urlencode(query)))


sync_url = _make_sync_url(_raw_db_url)

config = context.config
config.set_main_option("sqlalchemy.url", sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with sync engine."""
    connectable = create_engine(sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
