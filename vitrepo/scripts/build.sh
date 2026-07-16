#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[build] Project root: $ROOT_DIR"

echo "[build] Installing Python dependencies..."
pip install -r requirements.txt

# Determine safe pnpm command (Render environment safe, avoiding global permission errors)
PNPM_CMD="pnpm"
if ! command -v pnpm &> /dev/null; then
    echo "[build] pnpm not found globally. Using 'npx pnpm' as safe fallback..."
    PNPM_CMD="npx pnpm"
fi

echo "[build] Executing frontend build..."
cd "$ROOT_DIR/frontend"

# Always use pnpm if lockfile exists, otherwise fallback to npm
if [ -f "pnpm-lock.yaml" ] || [ -f "../pnpm-lock.yaml" ]; then
    echo "[build] Using pnpm (pnpm-lock.yaml detected)"
    $PNPM_CMD install --no-frozen-lockfile --production=false
else
    echo "[build] pnpm-lock.yaml not found. Falling back to npm install."
    npm install --prefer-offline --no-audit --no-fund --production=false
fi

echo "[build] Building frontend for production..."
if [ -f "pnpm-lock.yaml" ] || [ -f "../pnpm-lock.yaml" ]; then
    $PNPM_CMD run build
else
    npm run build
fi

echo "[build] Executing explorer build..."
cd "$ROOT_DIR/explorer"
npm install --prefer-offline --no-audit --no-fund
npm run build

# Database Schema Sync
echo "[build] Synchronizing database schema..."
cd "$ROOT_DIR"
export PYTHONPATH="${PYTHONPATH:-}:."
python3 scripts/init_db.py

# Auto-seed matches if empty
echo "[build] Checking match fixtures..."
python3 <<'PYEOF' || echo "[build] WARNING: Fixture auto-seed failed."
import asyncio
from app.db.database import AsyncSessionLocal
from app.db.models import Match
from sqlalchemy import select, func
import subprocess
import sys

async def check_and_seed():
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count(Match.id)))).scalar()
        if count == 0:
            print("[build] Database empty. Running import_fixtures.py...")
            subprocess.check_call([sys.executable, "scripts/import_fixtures.py"])
        else:
            print(f"[build] Database already contains {count} matches.")

if __name__ == "__main__":
    asyncio.run(check_and_seed())
PYEOF

echo "[build] Build sequence finalized successfully."
