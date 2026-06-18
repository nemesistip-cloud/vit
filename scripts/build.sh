#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[build] Project root: $ROOT_DIR"

echo "[build] Installing Python dependencies..."
pip install -r requirements.txt

if ! command -v pnpm &> /dev/null; then
    echo "[build] Installing pnpm..."
    npm install -g pnpm
fi

echo "[build] Executing frontend build..."
cd "$ROOT_DIR/frontend"
pnpm install --no-frozen-lockfile
pnpm run build

    # Always use pnpm if lockfile exists, otherwise fallback to npm
    if [ -f "pnpm-lock.yaml" ]; then
        echo "[build] Using pnpm (pnpm-lock.yaml detected)"
        pnpm install --frozen-lockfile
    elif [ -f "../pnpm-lock.yaml" ]; then
        echo "[build] Using pnpm (root pnpm-lock.yaml detected)"
        pnpm install --frozen-lockfile
    else
        echo "[build] pnpm-lock.yaml not found. Falling back to npm install."
        npm install --prefer-offline --no-audit --no-fund
    fi

    echo "[build] Building frontend for production..."
    if command -v pnpm &> /dev/null; then
        pnpm run build
    else
        npm run build
    fi
fi

# Database Schema Sync
echo "[build] Synchronizing database schema..."
export PYTHONPATH="${PYTHONPATH:-}:."
python3 <<'PYEOF' || echo "[build] WARNING: Database schema sync failed. Check DATABASE_URL."
import asyncio
import os
import sys
sys.path.append(os.getcwd())

async def sync_schema():
    try:
        from app.db.database import engine, Base
        import app.db.models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print('[build] DB Schema: All tables verified/created.')
        await engine.dispose()
    except Exception as e:
        print(f'[build] DB Sync Error: {e}')

if __name__ == "__main__":
    asyncio.run(sync_schema())
PYEOF

echo "[build] Build sequence finalized successfully."
