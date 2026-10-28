#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[build] Project root: $ROOT_DIR"

echo "[build] Installing Python dependencies..."
python3 -m pip install --upgrade "pip>=26.2" "setuptools>=83.0.0" "wheel>=0.46.2"
pip install .

# Keep Render builds on the same pnpm major as CI and Docker.
PNPM_CMD="pnpm"
if ! command -v pnpm &> /dev/null || [[ "$(pnpm --version)" != 9.* ]]; then
    echo "[build] pnpm v9 is not available globally. Using 'npx --yes pnpm@9'..."
    PNPM_CMD="npx --yes pnpm@9"
fi

echo "[build] Executing frontend build..."
cd "$ROOT_DIR/frontend"

# Always use pnpm if lockfile exists, otherwise fallback to npm
if [ -f "$ROOT_DIR/pnpm-lock.yaml" ]; then
    echo "[build] Using pnpm (pnpm-lock.yaml detected)"
    $PNPM_CMD install --frozen-lockfile --production=false
else
    echo "[build] pnpm-lock.yaml not found. Falling back to npm."
    if [ -f "$ROOT_DIR/package-lock.json" ]; then
        npm ci --prefer-offline --no-audit --no-fund --production=false
    else
        npm install --prefer-offline --no-audit --no-fund --production=false
    fi
fi

echo "[build] Building frontend for production..."
if [ -f "$ROOT_DIR/pnpm-lock.yaml" ]; then
    $PNPM_CMD run build
else
    npm run build
fi

echo "[build] Executing explorer build..."
cd "$ROOT_DIR/explorer"
if [ -f "$ROOT_DIR/pnpm-lock.yaml" ]; then
    echo "[build] Using dependencies installed from the frozen pnpm workspace lockfile"
    $PNPM_CMD run build
else
    if [ -f "package-lock.json" ]; then
        npm ci --prefer-offline --no-audit --no-fund
    else
        npm install --prefer-offline --no-audit --no-fund
    fi
    npm run build
fi

# Database Schema Sync
echo "[build] Synchronizing database schema..."
cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR/backend:$ROOT_DIR:${PYTHONPATH:-}"
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
