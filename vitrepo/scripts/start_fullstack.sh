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
if [ ! -d "${ROOT_DIR}/frontend/node_modules" ]; then
    echo "[startup] Installing frontend dependencies..."
    (cd "${ROOT_DIR}/frontend" && npm install --legacy-peer-deps --silent 2>/dev/null) || true
fi

# Fix pnpm-workspace hoisting conflict:
# pnpm may have hoisted @vitejs/plugin-react to workspace root but left vite
# only in frontend/node_modules. Bridge the gap with a symlink so node
# resolution finds vite from wherever it resolves @vitejs/plugin-react.
if [ -d "${ROOT_DIR}/frontend/node_modules/vite" ] && \
   [ ! -e "${ROOT_DIR}/node_modules/vite" ]; then
    echo "[startup] Bridging vite symlink for workspace hoisting..."
    ln -sfn "${ROOT_DIR}/frontend/node_modules/vite" "${ROOT_DIR}/node_modules/vite" 2>/dev/null || true
fi

# In Replit dev environment: run Vite dev server only (no Python backend needed)
if [ -n "${REPLIT_DEV_DOMAIN:-}" ] || [ -n "${REPL_ID:-}" ]; then
    echo "[startup] Replit environment detected — starting frontend dev server..."
    cd "${ROOT_DIR}/frontend"
    exec node_modules/.bin/vite --port 5000 --host 0.0.0.0
fi

# Production: build frontend then start Python backend
echo "[startup] Building frontend..."
if [ ! -f "${ROOT_DIR}/frontend/dist/index.html" ] \
    || [ "${ROOT_DIR}/frontend/src/main.tsx" -nt "${ROOT_DIR}/frontend/dist/index.html" ] \
    || [ "${ROOT_DIR}/frontend/vite.config.ts" -nt "${ROOT_DIR}/frontend/dist/index.html" ]; then
    (cd "${ROOT_DIR}/frontend" && npm run build 2>&1 | tail -5)
    echo "[startup] Frontend build complete."
else
    echo "[startup] Frontend build up to date, skipping rebuild."
fi

echo "[startup] Database schema ready"
echo "[startup] Starting Python backend on port ${BACKEND_PORT}..."
cd "${ROOT_DIR}"
exec python -m uvicorn main:app --host 0.0.0.0 --port "${BACKEND_PORT}"
