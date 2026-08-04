#!/usr/bin/env python3
"""
scripts/reset_users.py — Wipe all users and related records for a fresh start.

Only runs when RESET_USERS_ON_BOOT=true is set in the environment.
Set RESET_USERS_ON_BOOT=false (or remove the var) after the first deploy
to prevent accidental future resets.

WARNING: Irreversible. All accounts, wallets, predictions, and audit logs
will be deleted. ensure_admin.py (which runs next) creates a fresh admin
account from ADMIN_EMAIL / ADMIN_PASSWORD.
"""
import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="[reset_users] %(message)s")
log = logging.getLogger(__name__)

if os.getenv("RESET_USERS_ON_BOOT", "").strip().lower() != "true":
    log.info("RESET_USERS_ON_BOOT not set — skipping user reset.")
    sys.exit(0)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if "postgres" not in DATABASE_URL.lower():
    log.error("No PostgreSQL DATABASE_URL — cannot reset users.")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tables in FK-safe deletion order (children before parents).
_TABLES = [
    "audit_logs",
    "wallet_transactions",
    "withdrawal_requests",
    "savings_vaults",
    "p2p_orders",
    "p2p_offers",
    "wallets",
    "predictions",
    "match_predictions",
    "user_subscriptions",
    "notifications",
    "kyc_submissions",
    "developer_api_keys",
    "developer_apps",
    "trust_scores",
    "governance_votes",
    "reward_payouts",
    "user_storage_nodes",
    "agent_tasks",
    "webhook_events",
    "user_sessions",
    "users",
]


async def reset() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    # Normalise URL for asyncpg
    url = DATABASE_URL
    for old, new in [
        ("postgresql+asyncpg://", "postgresql+asyncpg://"),
        ("postgresql://", "postgresql+asyncpg://"),
        ("postgres://", "postgresql+asyncpg://"),
    ]:
        if url.startswith(old):
            url = new + url[len(old):]
            break

    engine = create_async_engine(url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        async with db.begin():
            cleared: dict = {}
            for table in _TABLES:
                try:
                    result = await db.execute(text(f"DELETE FROM {table}"))
                    cleared[table] = result.rowcount
                    if result.rowcount > 0:
                        log.info("  %-32s %d rows deleted", table, result.rowcount)
                except Exception as exc:
                    log.warning("  %-32s skipped (%s)", table, exc)

            total = sum(cleared.values())
            log.info(
                "Reset complete — %d total rows deleted across %d tables.",
                total,
                len([v for v in cleared.values() if v > 0]),
            )

    await engine.dispose()
    log.info("User reset finished. ensure_admin.py will create the fresh admin account.")


if __name__ == "__main__":
    asyncio.run(reset())
