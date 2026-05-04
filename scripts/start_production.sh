#!/usr/bin/env bash
# Production startup — FastAPI only (uvicorn on port 5000).
# The built frontend (frontend/dist) is served directly by FastAPI's StaticFiles mount.
# This script is used by Replit deployment; never run Vite in production.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-5000}"
WORKERS="${WEB_CONCURRENCY:-2}"

# v4.10 — activate trained .pkl weights in production
export USE_REAL_ML_MODELS="${USE_REAL_ML_MODELS:-true}"

echo "[production] Running database schema setup..."
python - <<'PYEOF'
import asyncio, os

async def ensure_schema():
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
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # PostgreSQL-safe column additions
            await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id INTEGER')
            await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS was_correct BOOLEAN')
            await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS settled_profit DOUBLE PRECISION')
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(20) DEFAULT 'none'")
            await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_submitted_at TIMESTAMP WITH TIME ZONE')
            await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_data JSON')
            await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak INTEGER DEFAULT 0')
            await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS best_streak INTEGER DEFAULT 0')
            await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS total_xp INTEGER DEFAULT 0')
        print('[production] Database schema ready')
    except Exception as e:
        print(f'[production] DB schema warning: {e}')

asyncio.run(ensure_schema())
PYEOF

echo "[production] Starting VIT backend with gunicorn on port ${PORT} (workers=${WORKERS})..."
exec gunicorn main:app \
    --bind "0.0.0.0:${PORT}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WORKERS}" \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
