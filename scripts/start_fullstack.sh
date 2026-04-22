#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5000}"

# v4.10.0 (Phase B) — Activate trained .pkl weights by default for the
# 12-model ensemble. Exported here so it wins over the .env default
# (load_dotenv runs with override=False, so the shell value takes precedence).
export USE_REAL_ML_MODELS="${USE_REAL_ML_MODELS:-true}"

if command -v fuser >/dev/null 2>&1; then
    fuser -k "${BACKEND_PORT}/tcp" >/dev/null 2>&1 || true
    fuser -k "${FRONTEND_PORT}/tcp" >/dev/null 2>&1 || true
fi

echo "[startup] Installing frontend dependencies..."
cd frontend && npm install --prefer-offline --silent 2>/dev/null || true && cd ..

echo "[startup] Starting frontend on port ${FRONTEND_PORT}..."
cd frontend
npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" &
FRONTEND_PID=$!
cd ..

echo "[startup] Running database schema setup..."
python -c "
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
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if conn.dialect.name == 'sqlite':
                cols = (await conn.exec_driver_sql('PRAGMA table_info(predictions)')).fetchall()
                col_names = {row[1] for row in cols}
                if 'user_id' not in col_names:
                    await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN user_id INTEGER')
                user_cols = (await conn.exec_driver_sql('PRAGMA table_info(users)')).fetchall()
                user_col_names = {row[1] for row in user_cols}
                user_additions = {
                    'kyc_status': \"VARCHAR(20) DEFAULT 'none'\",
                    'kyc_submitted_at': 'DATETIME',
                    'kyc_data': 'JSON',
                    'current_streak': 'INTEGER DEFAULT 0',
                    'best_streak': 'INTEGER DEFAULT 0',
                    'total_xp': 'INTEGER DEFAULT 0',
                }
                for col, ddl in user_additions.items():
                    if col not in user_col_names:
                        await conn.exec_driver_sql(f'ALTER TABLE users ADD COLUMN {col} {ddl}')
            else:
                await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id INTEGER')
                await conn.exec_driver_sql(\"ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(20) DEFAULT 'none'\")
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_submitted_at TIMESTAMP WITH TIME ZONE')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_data JSON')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak INTEGER DEFAULT 0')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS best_streak INTEGER DEFAULT 0')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS total_xp INTEGER DEFAULT 0')
        print('[startup] Database schema ready')
    except Exception as e:
        print(f'[startup] DB schema warning: {e}')

asyncio.run(ensure_schema())
" || echo "[startup] DB schema setup skipped"

echo "[startup] Starting backend on port ${BACKEND_PORT}..."
python -m uvicorn main:app --host 0.0.0.0 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

trap 'echo "[shutdown] Stopping services..."; kill $FRONTEND_PID $BACKEND_PID 2>/dev/null || true' EXIT
wait
