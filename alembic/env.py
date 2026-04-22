# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from alembic import context

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.db.models import Base
import app.db.models
import app.modules.wallet.models
import app.modules.blockchain.models
import app.modules.training.models
import app.modules.ai.models
import app.data.models
import app.modules.notifications.models
import app.modules.marketplace.models
import app.modules.trust.models
import app.modules.bridge.models
import app.modules.developer.models
import app.modules.governance.models
import app.modules.referral.models
from app.db.database import DATABASE_URL

config = context.config

# Convert async URL to sync URL for Alembic (sync engine only)
if "aiosqlite" in DATABASE_URL:
    sync_url = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
elif "asyncpg" in DATABASE_URL:
    sync_url = DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
    # Remove sslmode if present since asyncpg url may have it stripped
    from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
    parsed = urlparse(sync_url)
    query = dict(parse_qsl(parsed.query))
    query.pop("sslmode", None)
    sync_url = urlunparse(parsed._replace(query=urlencode(query)))
else:
    sync_url = DATABASE_URL

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
