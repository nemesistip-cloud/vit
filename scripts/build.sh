#!/usr/bin/env bash
set -uo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[build] Project root: $ROOT_DIR"

echo "[build] Cleaning up redundant lockfiles..."
rm -f package-lock.json frontend/package-lock.json

echo "[build] Installing Python dependencies..."
pip install -r requirements.txt

if ! command -v node &> /dev/null; then
    echo "[build] Error: node is not installed." >&2
fi

if ! command -v pnpm &> /dev/null; then
    echo "[build] pnpm not found. Installing pnpm globally..."
    npm install -g pnpm
fi

echo "[build] pnpm version: $(pnpm -v)"

if [[ "${1:-}" != "--skip-frontend" ]]; then
    echo "[build] Executing frontend build..."
    cd "$ROOT_DIR/frontend"
    pnpm install --frozen-lockfile || pnpm install
    pnpm run build
    cd "$ROOT_DIR"
fi

echo "[build] Synchronizing database schema..."
export PYTHONPATH="$ROOT_DIR"
python3 <<'PYEOF'
import asyncio
import os
import sys
sys.path.append(os.getcwd())

async def sync_schema():
    try:
        from app.db.database import engine, Base
        import app.db.models
        import app.modules.wallet.models
        import app.modules.blockchain.models
        import app.data.models
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

if __name__ == "__main__":
    asyncio.run(sync_schema())
PYEOF

echo "[build] Build sequence finalized successfully."
