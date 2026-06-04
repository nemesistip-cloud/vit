#!/usr/bin/env bash
# Production startup — FastAPI only (uvicorn on port $PORT).
# The built frontend (frontend/dist) is served directly by FastAPI's StaticFiles mount.
# This script is used by Replit deployment; never run Vite in production.
#
# NOTE: Single worker only — the app has background agents, WebSocket connections,
# and in-memory state (rate limiter, Elo store) that must live in one process.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-8080}"
APP_VERSION="5.5.0"

# Signal to app that we are in production — triggers full model loading,
# disables ephemeral JWT key warnings, and activates all 13 ensemble models.
# Works on Replit (REPLIT_DEPLOYMENT is set automatically) AND on Render/VPS.
export ENVIRONMENT="${ENVIRONMENT:-production}"
export USE_REAL_ML_MODELS="${USE_REAL_ML_MODELS:-true}"
export ML_MODEL_CACHE_ENABLED="${ML_MODEL_CACHE_ENABLED:-true}"

echo "[production] VIT Sports Analytics Network v${APP_VERSION}"
echo "[production] Environment: ${ENVIRONMENT} | Port: ${PORT}"

if [ -d "frontend/dist" ]; then
    echo "[production] Frontend assets found in frontend/dist"
else
    echo "[production] WARNING: frontend/dist not found. Frontend may not be served."
fi

echo "[production] Running database schema setup..."
python - <<'PYEOF'
import asyncio, os, time

async def ensure_schema():
    max_retries = 3
    for attempt in range(max_retries):
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
            import app.modules.prophecy_chain.models
            import app.modules.academy.models
            import app.modules.ai_core.models
            import app.modules.quant.models

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                # PostgreSQL-safe column additions
                sql_cmds = [
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
                    "ALTER TABLE wallets ADD COLUMN IF NOT EXISTS staked_vitcoin_balance NUMERIC(20, 8) DEFAULT 0"
                ]
                for cmd in sql_cmds:
                    await conn.exec_driver_sql(cmd)

            await engine.dispose()
            print("[production] Database schema ready")
            return
        except Exception as e:
            msg = str(e).lower()
            is_transient = any(x in msg for x in ["connection was closed", "not connected", "pool", "broken pipe", "protocol error", "timeout"])
            if is_transient and attempt < max_retries - 1:
                wait = (attempt + 1) * 2
                print(f"[production] DB schema transient error (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"[production] DB schema warning: {e}")
                try:
                    from app.db.database import engine
                    await engine.dispose()
                except: pass
                break

asyncio.run(ensure_schema())
PYEOF

echo "[production] Starting VIT Sports Analytics Network on port ${PORT}..."
exec python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --timeout-keep-alive 75 \
    --log-level info
