#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[build] Cleaning up redundant lockfiles..."
rm -f package-lock.json frontend/package-lock.json

echo "[build] Installing Python dependencies..."
pip install -r requirements.txt

# Ensure node is available
if ! command -v node &> /dev/null; then
    echo "[build] Error: node is not installed." >&2
    exit 1
fi

echo "[build] Using pnpm version: $(pnpm -v)"

# Ensure pnpm is available
if ! command -v pnpm &> /dev/null; then
    echo "[build] pnpm not found. Installing pnpm globally..."
    npm install -g pnpm
fi

echo "[build] pnpm version: $(pnpm -v)"

# Skip frontend build if --skip-frontend is passed
if [[ "${1:-}" != "--skip-frontend" ]]; then
    echo "[build] Executing frontend build..."

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
    cd ..
fi

# Database Schema Sync
echo "[build] Synchronizing database schema..."
export PYTHONPATH=$PYTHONPATH:.
python3 <<'PYEOF' || echo "[build] WARNING: Database schema sync failed. Check DATABASE_URL."
import asyncio
import os
import sys

async def sync_schema():
    try:
        from app.db.database import engine, Base
        # Core Models
        import app.db.models
        import app.modules.wallet.models
        import app.modules.blockchain.models
        import app.data.models
        # Extension Modules
        import app.modules.notifications.models
        import app.modules.marketplace.models
        import app.modules.trust.models
        import app.modules.bridge.models
        import app.modules.developer.models
        import app.modules.governance.models
        import app.modules.network.models
        import app.modules.tasks.models
        import app.modules.rewards.models
        import app.modules.referral.models
        import app.modules.smart_contracts.models
        import app.modules.treasury.models
        import app.modules.merit.models
        import app.modules.identity.models
        import app.modules.kyc.models
        import app.modules.prophecy_chain.models
        import app.modules.quant.models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print('[build] DB Schema: All tables verified/created.')
        await engine.dispose()
    except Exception as e:
        print(f'[build] DB Sync Error: {e}')
        sys.exit(0) # Non-fatal for the build process itself

if __name__ == "__main__":
    asyncio.run(sync_schema())
PYEOF

echo "[build] Build sequence finalized successfully."
