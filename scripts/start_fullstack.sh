#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5000}"

export USE_REAL_ML_MODELS="${USE_REAL_ML_MODELS:-true}"

# Kill any stale processes holding our ports.
# We use /proc/net/tcp to find PIDs without needing fuser/ss/lsof.
kill_port() {
    local port=$1
    local hex_port
    hex_port=$(printf '%04X' "$port")
    local inode
    inode=$(awk "/00000000:${hex_port} / {print \$10}" /proc/net/tcp /proc/net/tcp6 2>/dev/null | head -1)
    if [ -n "$inode" ]; then
        local pid
        pid=$(grep -rl "socket:\[${inode}\]" /proc/*/fd 2>/dev/null | grep -oP '(?<=/proc/)\d+' | head -1 || true)
        if [ -n "$pid" ] && [ "$pid" != "$$" ]; then
            echo "[startup] Killing stale process $pid on port $port"
            kill -TERM "$pid" 2>/dev/null || true
            sleep 1
            kill -KILL "$pid" 2>/dev/null || true
        fi
    fi
}

kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"
sleep 1

echo "[startup] Installing frontend dependencies..."
if [ ! -d "frontend/node_modules/@rollup/rollup-linux-x64-gnu" ] || [ ! -d "frontend/node_modules" ] || [ "frontend/package.json" -nt "frontend/node_modules/.package-lock.json" ]; then
    cd frontend && npm install --force --silent 2>/dev/null || true && cd ..
else
    echo "[startup] Frontend dependencies up to date, skipping install."
fi

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
            if conn.dialect.name == 'sqlite':
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
                task_cols = (await conn.exec_driver_sql('PRAGMA table_info(tasks)')).fetchall()
                task_col_names = {row[1] for row in task_cols}
                task_additions = {
                    'action_url':   'TEXT',
                    'action_label': 'TEXT',
                }
                for col, ddl in task_additions.items():
                    if col not in task_col_names:
                        await conn.exec_driver_sql(f'ALTER TABLE tasks ADD COLUMN {col} {ddl}')
                stake_cols = (await conn.exec_driver_sql('PRAGMA table_info(user_stakes)')).fetchall()
                stake_col_names = {row[1] for row in stake_cols}
                if 'ah_line' not in stake_col_names:
                    await conn.exec_driver_sql('ALTER TABLE user_stakes ADD COLUMN ah_line REAL')
                if 'prediction' in stake_col_names:
                    pass  # SQLite cannot ALTER column type; String(10) is enforced at ORM level only
            else:
                await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id INTEGER')
                await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS was_correct BOOLEAN')
                await conn.exec_driver_sql('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS settled_profit DOUBLE PRECISION')
                await conn.exec_driver_sql(\"ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(20) DEFAULT 'none'\")
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_submitted_at TIMESTAMP WITH TIME ZONE')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_data JSON')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak INTEGER DEFAULT 0')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS best_streak INTEGER DEFAULT 0')
                await conn.exec_driver_sql('ALTER TABLE users ADD COLUMN IF NOT EXISTS total_xp INTEGER DEFAULT 0')
                await conn.exec_driver_sql('ALTER TABLE user_stakes ADD COLUMN IF NOT EXISTS ah_line NUMERIC(5,2)')
                try:
                    await conn.exec_driver_sql('ALTER TABLE user_stakes ALTER COLUMN prediction TYPE VARCHAR(20)')
                except Exception:
                    pass
                # marketplace_listings: performance columns (v7)
                for _col, _ddl in [
                    ('accuracy_rate',   'DOUBLE PRECISION DEFAULT 0.0'),
                    ('roi',             'DOUBLE PRECISION DEFAULT 0.0'),
                    ('clv_correlation', 'DOUBLE PRECISION DEFAULT 0.0'),
                    ('is_verified',     'BOOLEAN DEFAULT FALSE'),
                    ('total_staked',    'NUMERIC(20,8) DEFAULT 0'),
                    ('staker_count',    'INTEGER DEFAULT 0'),
                ]:
                    try:
                        await conn.exec_driver_sql(f'ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS {_col} {_ddl}')
                    except Exception:
                        pass
                # validator_profiles: specialist_leagues (v7)
                try:
                    await conn.exec_driver_sql('ALTER TABLE validator_profiles ADD COLUMN IF NOT EXISTS specialist_leagues VARCHAR(255)')
                except Exception:
                    pass
        print('[startup] Database schema ready')
    except Exception as e:
        print(f'[startup] DB schema warning: {e}')

asyncio.run(ensure_schema())
" || echo "[startup] DB schema setup skipped"

echo "[startup] Starting backend on port ${BACKEND_PORT}..."
python -m uvicorn main:app --host 0.0.0.0 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

echo "[startup] Waiting for backend to be ready..."
WAIT_SECS=0
until curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; do
    sleep 1
    WAIT_SECS=$((WAIT_SECS + 1))
    if [ $WAIT_SECS -ge 60 ]; then
        echo "[startup] Backend did not become ready within 60s — starting frontend anyway"
        break
    fi
done
echo "[startup] Backend ready after ${WAIT_SECS}s"

echo "[startup] Starting frontend on port ${FRONTEND_PORT}..."
kill_port "$FRONTEND_PORT"
sleep 1
cd frontend
npx vite --host 0.0.0.0 --port "${FRONTEND_PORT}" &
FRONTEND_PID=$!
cd ..

trap 'echo "[shutdown] Stopping services..."; kill $FRONTEND_PID $BACKEND_PID 2>/dev/null || true' EXIT
wait
