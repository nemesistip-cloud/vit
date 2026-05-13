#!/usr/bin/env bash
# Build-phase script: installs frontend deps and builds the bundle.
# Python packages (.pythonlibs) are included in the deployment image — no pip needed here.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[build] Installing frontend dependencies..."
cd frontend
npm install --prefer-offline --silent 2>/dev/null || npm install

echo "[build] Building frontend..."
npm run build
echo "[build] Done — frontend bundle written to frontend/dist"
