# app/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.config import DATABASE_URL

_raw_url = DATABASE_URL

# Guarantee asyncpg driver — replace any sync postgres scheme and remove unsupported sslmode params
def _make_async_url(url: str) -> str:
    # If already has async driver, return as-is
    if "aiosqlite" in url or "asyncpg" in url:
        return url

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # asyncpg does not accept sslmode as a direct connect keyword argument
    query.pop("sslmode", None)

    scheme = parsed.scheme
    if scheme in ("postgresql", "postgres") or scheme == "postgresql+psycopg2":
        scheme = "postgresql+asyncpg"
    elif scheme == "sqlite":
        scheme = "sqlite+aiosqlite"

    safe_query = urlencode(query)
    return urlunparse(parsed._replace(scheme=scheme, query=safe_query))

DATABASE_URL = _make_async_url(_raw_url)

_is_sqlite = "aiosqlite" in DATABASE_URL

# SQLite needs NullPool (no connection pool); PostgreSQL uses queue pool
if _is_sqlite:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )

    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()
else:
    # Reduced pool sizes for Render Free Tier (25 connection limit)
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        connect_args={"ssl": True},
    )

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
