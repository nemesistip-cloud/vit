#!/usr/bin/env bash
# Production startup — FastAPI + Integrated Background Agents.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-10000}"
APP_VERSION="5.5.0"

export ENVIRONMENT="${ENVIRONMENT:-production}"
export PYTHONPATH="${PYTHONPATH:-}:."

# Auto-generate ADMIN_PASSWORD
if [ -z "${ADMIN_PASSWORD:-}" ]; then
    _AUTO_PASS="$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(24)))")"
    export ADMIN_PASSWORD="${_AUTO_PASS}"
fi

echo "[production] VIT Sports Analytics Network v${APP_VERSION}"
echo "[production] Hybrid Mode: ML + SCIE Active"

# Apply any pending Alembic migrations before boot. Safe to run on every
# deploy/restart — Alembic no-ops if the DB is already at the latest
# revision(s). This repo has two divergent migration heads, so we use
# `heads` (plural) rather than `head`. Only runs against Postgres; the
# SQLite dev fallback uses create_all() elsewhere and doesn't need this.
if [ -n "${DATABASE_URL:-}" ] && echo "${DATABASE_URL}" | grep -q "postgres"; then
    echo "[production] Running database migrations (alembic upgrade heads)..."
    if ! alembic upgrade heads; then
        echo "[production] WARNING: alembic upgrade failed — continuing startup, but the app may hit 'relation does not exist' errors until this is resolved." >&2
    fi
else
    echo "[production] Skipping alembic migrations (no Postgres DATABASE_URL detected)."
fi

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
