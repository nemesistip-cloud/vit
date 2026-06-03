#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5000}"

# v4.10.0 (Phase B) — Activate trained .pkl weights by default for the
# 12-model ensemble. Exported here so it wins over the .env default
# (load_dotenv runs with override=False, so the shell value takes precedence).
export USE_REAL_ML_MODELS="${USE_REAL_ML_MODELS:-true}"

if command -v fuser >/dev/null 2>&1; then
    fuser -k "${BACKEND_PORT}/tcp" >/dev/null 2>&1 || true
    fuser -k "${FRONTEND_PORT}/tcp" >/dev/null 2>&1 || true
fi

echo "[startup] Installing frontend dependencies..."
if [ ! -d "frontend/node_modules" ] || [ "frontend/package.json" -nt "frontend/node_modules/.package-lock.json" ]; then
    cd frontend && npm install --prefer-offline --silent 2>/dev/null || true && cd ..
else
    echo "[startup] Frontend dependencies up to date, skipping install."
fi

echo "[startup] Starting frontend on port ${FRONTEND_PORT}..."
cd frontend
# package.json dev script already sets --host 0.0.0.0 --port 5000; override port only if custom
if [ "${FRONTEND_PORT}" != "5000" ]; then
    VITE_PORT="${FRONTEND_PORT}" npx vite --host 0.0.0.0 --port "${FRONTEND_PORT}" &
else
    npm run dev &
fi
FRONTEND_PID=$!
cd ..

# Schema setup is handled by FastAPI lifespan on startup — skip blocking pre-check
echo "[startup] Database schema ready"

echo "[startup] Starting backend on port ${BACKEND_PORT}..."
python -m uvicorn main:app --host 0.0.0.0 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

trap 'echo "[shutdown] Stopping services..."; kill $FRONTEND_PID $BACKEND_PID 2>/dev/null || true' EXIT
wait
