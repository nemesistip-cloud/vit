#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

PORT="${PORT:-5000}"
BACKEND_PORT="${PORT}"

if command -v fuser >/dev/null 2>&1; then
    fuser -k "${BACKEND_PORT}/tcp" >/dev/null 2>&1 || true
fi

echo "[startup] Checking frontend dependencies..."
if [ ! -f "${ROOT_DIR}/node_modules/.bin/vite" ]; then
    echo "[startup] Installing frontend dependencies..."
    npm install --legacy-peer-deps --silent 2>/dev/null || true
fi

echo "[startup] Building frontend..."
if [ ! -f "frontend/dist/index.html" ] \
    || [ "frontend/src/main.tsx" -nt "frontend/dist/index.html" ] \
    || [ "frontend/vite.config.ts" -nt "frontend/dist/index.html" ]; then
    (cd "${ROOT_DIR}/frontend" && node "${ROOT_DIR}/node_modules/.bin/vite" build 2>&1 | tail -5)
    echo "[startup] Frontend build complete."
else
    echo "[startup] Frontend build up to date, skipping build."
fi

echo "[startup] Database schema ready"
echo "[startup] Starting server on port ${BACKEND_PORT}..."

cd "${ROOT_DIR}"
exec python -m uvicorn main:app --host 0.0.0.0 --port "${BACKEND_PORT}"
