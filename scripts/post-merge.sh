#!/usr/bin/env bash
# Post-merge setup: runs automatically after a task branch is merged into main.
# Installs/updates frontend deps and applies any new DB schema migrations.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[post-merge] Installing frontend dependencies..."
cd frontend
npm install --prefer-offline 2>/dev/null || npm install
cd ..

echo "[post-merge] Running database schema setup..."
python - <<'PYEOF'
import asyncio

async def run():
    try:
        from app.db.database import engine, Base
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
        import app.modules.did.models
        import app.modules.network.models
        import app.modules.tasks.models
        import app.modules.rewards.models
        import app.modules.referral.models
        import app.modules.smart_contracts.models
        import app.modules.treasury.models
        import app.modules.merit.models
        import app.modules.ai_verification.models
        import app.modules.security.models
        import app.modules.subchain.models
        import app.modules.agent_registry.models
        import app.modules.storage_verification.models
        import app.modules.identity.models
        import app.modules.kyc.models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            dialect = conn.dialect.name
            if dialect == "sqlite":
                for tbl, col, ddl in [
                    ("predictions", "user_id",         "INTEGER"),
                    ("predictions", "was_correct",      "BOOLEAN"),
                    ("predictions", "settled_profit",   "REAL"),
                    ("users",       "kyc_status",       "VARCHAR(20) DEFAULT 'none'"),
                    ("users",       "kyc_submitted_at", "DATETIME"),
                    ("users",       "kyc_data",         "JSON"),
                    ("users",       "current_streak",   "INTEGER DEFAULT 0"),
                    ("users",       "best_streak",      "INTEGER DEFAULT 0"),
                    ("users",       "total_xp",         "INTEGER DEFAULT 0"),
                    ("tasks",       "action_url",       "TEXT"),
                    ("tasks",       "action_label",     "TEXT"),
                ]:
                    rows = (await conn.exec_driver_sql(f"PRAGMA table_info({tbl})")).fetchall()
                    if col not in {r[1] for r in rows}:
                        await conn.exec_driver_sql(f"ALTER TABLE {tbl} ADD COLUMN {col} {ddl}")
            else:
                for stmt in [
                    "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id INTEGER",
                    "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS was_correct BOOLEAN",
                    "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS settled_profit DOUBLE PRECISION",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(20) DEFAULT 'none'",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_submitted_at TIMESTAMP WITH TIME ZONE",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_data JSON",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak INTEGER DEFAULT 0",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS best_streak INTEGER DEFAULT 0",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS total_xp INTEGER DEFAULT 0",
                    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS action_url TEXT",
                    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS action_label TEXT",
                ]:
                    await conn.exec_driver_sql(stmt)
        print("[post-merge] Schema ready.")
    except Exception as e:
        print(f"[post-merge] Schema warning (non-fatal): {e}")

asyncio.run(run())
PYEOF

echo "[post-merge] Done."
