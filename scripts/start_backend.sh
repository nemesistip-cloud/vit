#!/usr/bin/env bash
# Start the FastAPI backend for local development (Replit)
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${BACKEND_PORT:-8000}"
export PYTHONPATH="${PYTHONPATH:-}:."
export ENVIRONMENT="${ENVIRONMENT:-development}"

echo "[backend] VIT Network backend starting on port ${PORT}..."

exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --reload \
    --log-level info
