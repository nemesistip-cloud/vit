#!/usr/bin/env bash
# Build-phase script: installs Python packages + builds the frontend bundle.
# Run by Replit deployment as the build command — must exit cleanly.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[build] Installing Python dependencies..."
pip install -r requirements.txt --quiet --no-cache-dir

echo "[build] Installing frontend dependencies..."
cd frontend
npm install --prefer-offline --silent 2>/dev/null || npm install

echo "[build] Building frontend..."
npm run build
echo "[build] Done — frontend bundle written to frontend/dist"
