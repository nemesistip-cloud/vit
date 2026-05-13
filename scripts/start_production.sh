#!/usr/bin/env bash
# Production run script — skips frontend build (handled by build_frontend.sh).
# Runs DB schema setup then starts FastAPI via gunicorn.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-5000}"
WORKERS="${WEB_CONCURRENCY:-1}"

# Force production environment regardless of shared env vars
export ENVIRONMENT="production"
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
        import app.modules.identity.models
        import app.modules.kyc.models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            dialect = conn.dialect.name
            if dialect == 'sqlite':
                cols = (await conn.exec_driver_sql('PRAGMA table_info(predictions)')).fetchall()
                col_names = {row[1] for row in cols}
                pred_additions = {
                    'user_id': 'INTEGER',
                    'was_correct': 'BOOLEAN',
                    'settled_profit': 'REAL',
                }
                for col, ddl in pred_additions.items():
                    if col not in col_names:
                        await conn.exec_driver_sql(f'ALTER TABLE predictions ADD COLUMN {col} {ddl}')
                user_cols = (await conn.exec_driver_sql('PRAGMA table_info(users)')).fetchall()
                user_col_names = {row[1] for row in user_cols}
                user_additions = {
                    'kyc_status': "VARCHAR(20) DEFAULT 'none'",
                    'kyc_submitted_at': 'DATETIME',
                    'kyc_data': 'JSON',
                    'current_streak': 'INTEGER DEFAULT 0',
                    'best_streak': 'INTEGER DEFAULT 0',
                    'total_xp': 'INTEGER DEFAULT 0',
                }
                for col, ddl in user_additions.items():
                    if col not in user_col_names:
                        await conn.exec_driver_sql(f'ALTER TABLE users ADD COLUMN {col} {ddl}')
                task_cols = (await conn.exec_driver_sql('PRAGMA table_info(tasks)')).fetchall()
                task_col_names = {row[1] for row in task_cols}
                task_additions = {
                    'action_url':   'TEXT',
                    'action_label': 'TEXT',
                }
                for col, ddl in task_additions.items():
                    if col not in task_col_names:
                        await conn.exec_driver_sql(f'ALTER TABLE tasks ADD COLUMN {col} {ddl}')
            else:
                # PostgreSQL path
                await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id INTEGER')
                await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS was_correct BOOLEAN')
                await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS settled_profit DOUBLE PRECISION')
                await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(20) DEFAULT 'none'")
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_submitted_at TIMESTAMP WITH TIME ZONE')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_data JSON')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak INTEGER DEFAULT 0')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS best_streak INTEGER DEFAULT 0')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS total_xp INTEGER DEFAULT 0')
                await conn.exec_driver_sql('ALTER TABLE tasks ADD COLUMN IF NOT EXISTS action_url TEXT')
                await conn.exec_driver_sql('ALTER TABLE tasks ADD COLUMN IF NOT EXISTS action_label TEXT')
                await conn.exec_driver_sql('ALTER TABLE user_stakes ADD COLUMN IF NOT EXISTS ah_line NUMERIC(5,2)')
                try:
                    await conn.exec_driver_sql('ALTER TABLE user_stakes ALTER COLUMN prediction TYPE VARCHAR(20)')
                except Exception:
                    pass
        print('[production] Database schema ready')
    except Exception as e:
        print(f'[production] DB schema warning: {e}')

asyncio.run(ensure_schema())
PYEOF

echo "[production] Starting VIT backend with gunicorn on port ${PORT} (workers=${WORKERS})..."
GUNICORN_BIN="$(python -c 'import sys, os; print(os.path.join(os.path.dirname(sys.executable), "gunicorn"))' 2>/dev/null || echo gunicorn)"
exec "$GUNICORN_BIN" main:app \
    --bind "0.0.0.0:${PORT}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WORKERS}" \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
