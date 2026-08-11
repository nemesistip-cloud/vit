"""scripts/run_migrations.py
Production-safe Alembic migration runner with PostgreSQL advisory lock.

Guarantees:
  - Only one instance migrates at a time (advisory lock prevents races on
    rolling deploys or multi-worker restarts).
  - Idempotent: safe to call on every startup; no-ops if nothing is pending.
  - Rolls back safely: Alembic's per-migration DDL transactions ensure that a
    failed migration does not leave the schema partially applied.
  - Exits with code 1 on failure so the caller can surface the error.

Usage:
    python3 scripts/run_migrations.py
"""

import asyncio
import logging
import os
import subprocess
import sys
import ssl
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

logging.basicConfig(
    level=logging.INFO,
    format="[migration] %(levelname)s %(message)s",
)
logger = logging.getLogger("migration")

# Unique advisory lock ID for this application (arbitrary but consistent).
ADVISORY_LOCK_ID = 7764001

ALEMBIC_TIMEOUT = 180  # seconds


def _make_async_url(url: str) -> str:
    """Return a SQLAlchemy URL that explicitly uses asyncpg.

    Render exposes PostgreSQL URLs using the legacy ``postgres://`` scheme
    (and some environments use ``postgresql+psycopg2://``).  Passing either
    directly to ``create_async_engine`` makes SQLAlchemy select psycopg2,
    which is a synchronous driver and raises at startup.
    """
    if not url or "sqlite" in url:
        return url

    parsed = urlparse(url)
    if parsed.scheme not in {
        "postgres",
        "postgresql",
        "postgresql+psycopg2",
        "postgres+asyncpg",
        "postgresql+asyncpg",
    }:
        return url

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    # asyncpg uses the ``ssl`` connect argument instead of libpq's sslmode.
    query.pop("sslmode", None)
    return urlunparse(parsed._replace(scheme="postgresql+asyncpg", query=urlencode(query)))


def _async_connect_args(url: str) -> dict:
    """Configure TLS for external PostgreSQL providers such as Render."""
    host = urlparse(url).hostname or ""
    if host in {"", "localhost", "127.0.0.1", "helium"}:
        return {}

    ssl_context = ssl.create_default_context()
    # Managed providers commonly use a private or provider-issued CA.  The
    # database connection remains encrypted while matching the app's existing
    # production database configuration.
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return {"ssl": ssl_context}


def _check_alembic_state(conn_sync) -> str:
    """Return 'STAMP' for a fresh DB, 'UPGRADE' for an existing one."""
    from sqlalchemy import inspect as sa_inspect, text  # noqa: PLC0415

    inspector = sa_inspect(conn_sync)
    if not inspector.has_table("alembic_version"):
        return "STAMP"
    count = conn_sync.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar()
    return "STAMP" if count == 0 else "UPGRADE"


async def run_migrations() -> bool:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url or "postgres" not in database_url.lower():
        logger.info("No PostgreSQL DATABASE_URL — skipping migrations.")
        return True

    try:
        from sqlalchemy.ext.asyncio import create_async_engine  # noqa: PLC0415
        from sqlalchemy import text  # noqa: PLC0415

        async_url = _make_async_url(database_url)
        engine = create_async_engine(
            async_url,
            echo=False,
            pool_size=2,
            max_overflow=0,
            connect_args=_async_connect_args(async_url),
        )
    except Exception as exc:
        logger.error("Failed to create database engine: %s", exc)
        return False

    try:
        async with engine.begin() as conn:
            # Non-blocking advisory lock — if another instance holds it we skip.
            locked = await conn.scalar(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": ADVISORY_LOCK_ID},
            )
            if not locked:
                logger.info(
                    "Another instance holds the migration lock — skipping (not an error)."
                )
                return True

            logger.info("Advisory lock acquired (id=%d).", ADVISORY_LOCK_ID)

            try:
                action = await conn.run_sync(_check_alembic_state)
                logger.info("Alembic action determined: %s", action)

                cmd = (
                    ["alembic", "stamp", "heads"]
                    if action == "STAMP"
                    else ["alembic", "upgrade", "heads"]
                )
                label = "stamp heads" if action == "STAMP" else "upgrade heads"

                try:
                    # Try invoking the global alembic binary directly (Render/Docker standard)
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=ALEMBIC_TIMEOUT,
                    )
                except FileNotFoundError:
                    # Fallback to sys.executable -m alembic if alembic binary is not in PATH
                    logger.info("alembic binary not in PATH — falling back to sys.executable -m alembic")
                    cmd_fallback = (
                        [sys.executable, "-m", "alembic", "stamp", "heads"]
                        if action == "STAMP"
                        else [sys.executable, "-m", "alembic", "upgrade", "heads"]
                    )
                    result = subprocess.run(
                        cmd_fallback,
                        capture_output=True,
                        text=True,
                        timeout=ALEMBIC_TIMEOUT,
                    )

                if result.stdout:
                    logger.info("alembic %s stdout:\n%s", label, result.stdout.strip())
                if result.stderr:
                    logger.warning("alembic %s stderr:\n%s", label, result.stderr.strip())

                if result.returncode != 0:
                    logger.error(
                        "alembic %s exited with code %d — migration FAILED.",
                        label,
                        result.returncode,
                    )
                    return False

                logger.info("alembic %s completed successfully.", label)
                return True

            finally:
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": ADVISORY_LOCK_ID},
                )
                logger.info("Advisory lock released.")

    except subprocess.TimeoutExpired:
        logger.error("Migration timed out after %d seconds.", ALEMBIC_TIMEOUT)
        return False
    except Exception as exc:
        logger.error("Migration runner error: %s", exc, exc_info=True)
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(run_migrations())
    sys.exit(0 if success else 1)
