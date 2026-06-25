#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-5000}"
BACKEND_PORT="${PORT}"


if command -v fuser >/dev/null 2>&1; then
    fuser -k "${BACKEND_PORT}/tcp" >/dev/null 2>&1 || true
fi

echo "[startup] Installing frontend dependencies..."
if [ ! -d "frontend/node_modules" ] || [ "frontend/package.json" -nt "frontend/node_modules/.package-lock.json" ]; then
    cd frontend && npm install --prefer-offline --legacy-peer-deps --silent 2>/dev/null || true && cd ..
else
    echo "[startup] Frontend dependencies up to date, skipping install."
fi

echo "[startup] Building frontend..."
if [ ! -d "frontend/dist" ] || [ "frontend/src/main.tsx" -nt "frontend/dist/index.html" ] || [ "frontend/vite.config.ts" -nt "frontend/dist/index.html" ]; then
    cd frontend && /home/runner/workspace/node_modules/.bin/vite build --config vite.config.ts 2>&1 | tail -5 && cd ..
    echo "[startup] Frontend build complete."
else
    echo "[startup] Frontend build up to date, skipping build."
fi

echo "[startup] Database schema ready"

echo "[startup] Starting server on port ${BACKEND_PORT}..."
python -m uvicorn main:app --host 0.0.0.0 --port "${BACKEND_PORT}"
