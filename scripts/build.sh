#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "[build] Installing Python dependencies..."
pip install -r requirements.txt

# Ensure node is available
if ! command -v node &> /dev/null; then
    echo "[build] Error: node is not installed." >&2
    # Use return 1 in a subshell or just let it fail naturally
    false
fi

echo "[build] Node version: $(node -v)"

echo "[build] Installing frontend dependencies..."
cd frontend

# Detect lockfiles and use appropriate package manager
if [ -f "pnpm-lock.yaml" ]; then
    echo "[build] Using pnpm (pnpm-lock.yaml detected)"
    # Render should have pnpm if it detected the lockfile, but let's be safe
    pnpm install --frozen-lockfile
elif [ -f "package-lock.json" ]; then
    echo "[build] Using npm ci (package-lock.json detected)"
    npm ci --prefer-offline --no-audit --no-fund
else
    echo "[build] Using npm install fallback"
    npm install --prefer-offline --no-audit --no-fund
fi

echo "[build] Building frontend for production..."
if [ -f "pnpm-lock.yaml" ]; then
    pnpm run build
else
    npm run build
fi
cd ..

echo "[build] Running database schema setup..."
python -c "
import asyncio, os

async def ensure_schema():
    from app.db.database import engine, Base
    try:
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
                await conn.exec_driver_sql('ALTER TABLE tasks ADD COLUMN IF NOT EXISTS action_url TEXT')
                await conn.exec_driver_sql('ALTER TABLE tasks ADD COLUMN IF NOT EXISTS action_label TEXT')
        print('[build] Database schema ready')
    except Exception as e:
        print(f'[build] DB schema warning: {e}')
    finally:
        await engine.dispose()

asyncio.run(ensure_schema())
" || echo "[build] DB schema setup skipped"

echo "[build] Build complete."
