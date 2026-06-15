#!/usr/bin/env bash
# Production startup — FastAPI + Integrated Background Agents.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-10000}"
APP_VERSION="5.5.0"

export ENVIRONMENT="${ENVIRONMENT:-production}"
export USE_REAL_ML_MODELS="${USE_REAL_ML_MODELS:-true}"
export ML_MODEL_CACHE_ENABLED="${ML_MODEL_CACHE_ENABLED:-true}"

# Auto-generate ADMIN_PASSWORD
if [ -z "${ADMIN_PASSWORD:-}" ]; then
    _AUTO_PASS="$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(24)))")"
    export ADMIN_PASSWORD="${_AUTO_PASS}"
fi

echo "[production] VIT Sports Analytics Network v${APP_VERSION}"
echo "[production] Hybrid Mode: ML + SCIE Active"

# Run schema setup
bash scripts/build.sh --skip-frontend || true

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
