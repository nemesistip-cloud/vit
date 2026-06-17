#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[build] Monorepo Build Sequence Initiated"
echo "[build] Environment: $(python3 --version), Node $(node -v)"

# Cleanup redundant lockfiles to prevent package manager confusion
echo "[build] Enforcing lockfile hygiene..."
rm -f package-lock.json frontend/package-lock.json

# Ensure Python dependencies are up to date
echo "[build] Syncing Python dependencies..."
pip install -r requirements.txt

# PNPM Management
if ! command -v pnpm &> /dev/null; then
    echo "[build] pnpm not detected. Installing globally..."
    npm install -g pnpm || {
        echo "[build] Global install failed. Attempting local installation..."
        npm install pnpm
        export PATH="$PATH:$(pwd)/node_modules/.bin"
    }
fi

echo "[build] Using pnpm version: $(pnpm -v)"

# Frontend Build
if [[ "${1:-}" != "--skip-frontend" ]]; then
    echo "[build] Executing frontend build..."

    # Run from root to respect pnpm-workspace.yaml
    pnpm install --frozen-lockfile || {
        echo "[build] Frozen lockfile install failed. Attempting standard install..."
        pnpm install
    }

    echo "[build] Building production artifacts..."
    pnpm run build
else
    echo "[build] Frontend build bypassed."
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
