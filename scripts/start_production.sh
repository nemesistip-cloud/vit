#!/usr/bin/env bash
# Production startup — FastAPI + Integrated Background Agents.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-10000}"
APP_VERSION="5.5.0"

export ENVIRONMENT="${ENVIRONMENT:-production}"
export USE_REAL_ML_MODELS="${USE_REAL_ML_MODELS:-false}"
export ML_MODEL_CACHE_ENABLED="${ML_MODEL_CACHE_ENABLED:-false}"

# Auto-generate ADMIN_PASSWORD
if [ -z "${ADMIN_PASSWORD:-}" ]; then
    _AUTO_PASS="$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(24)))")"
    export ADMIN_PASSWORD="${_AUTO_PASS}"
fi

echo "[production] VIT Sports Analytics Network v${APP_VERSION}"
echo "[production] Hybrid Mode: ML + SCIE Active"

# Removed redundant scripts/build.sh call.
# Render runs build.sh during the deployment phase.

# Start FastAPI (Background Supervisor handles the agents)
echo "[production] Starting VIT Network on port ${PORT}..."
exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --timeout-keep-alive 75 \
    --log-level info
