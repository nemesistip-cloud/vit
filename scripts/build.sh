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

if [ -d "frontend" ]; then
    echo "[build] Executing frontend build..."
    cd "$ROOT_DIR/frontend"

    if [ -f "pnpm-lock.yaml" ]; then
        echo "[build] Using pnpm (pnpm-lock.yaml detected)"
        pnpm install --no-frozen-lockfile
        pnpm run build
    else
        echo "[build] pnpm-lock.yaml not found. Falling back to npm."
        npm install --prefer-offline --no-audit --no-fund
        npm run build
    fi
    cd "$ROOT_DIR"
fi

# Database Schema Sync
echo "[build] Synchronizing database schema..."
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
