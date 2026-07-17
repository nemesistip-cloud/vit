#!/usr/bin/env bash
# Production startup — FastAPI + Integrated Background Agents.
set -euo pipefail
cd "$(dirname "$0")/.."

# PORT: read from env (Render dashboard sets PORT=8000).
# Default to 8000 to match the Render dashboard value — do NOT hardcode 10000
# here since that would cause a mismatch and the service would bind on a port
# Render doesn't proxy.
PORT="${PORT:-8000}"
APP_VERSION="1.1.0"

export ENVIRONMENT="${ENVIRONMENT:-production}"
export PYTHONPATH="${PYTHONPATH:-}:."

# Auto-generate ADMIN_PASSWORD
if [ -z "${ADMIN_PASSWORD:-}" ]; then
    _AUTO_PASS="$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(24)))")"
    export ADMIN_PASSWORD="${_AUTO_PASS}"
fi

echo "[production] VIT Sports Analytics Network v${APP_VERSION}"
echo "[production] Hybrid Mode: ML + SCIE Active"

if [ -n "${DATABASE_URL:-}" ] && echo "${DATABASE_URL}" | grep -q "postgres"; then
    # Step 0 — Ensure all tables exist via SQLAlchemy create_all (safety net).
    # This is idempotent and handles fresh DBs where alembic hasn't run yet.
    echo "[production] Running DB table bootstrap (init_db.py)..."
    if ! python3 scripts/init_db.py; then
        echo "[production] WARNING: init_db failed — continuing." >&2
    fi

    # Step 1 — Pre-flight column guard (idempotent ALTER TABLE IF NOT EXISTS).
    # Runs BEFORE Alembic so that even if the migration chain is partially broken
    # the columns the ORM depends on are guaranteed to exist.
    echo "[production] Running pre-flight schema guard (ensure_columns.py)..."
    if ! python3 scripts/ensure_columns.py; then
        echo "[production] WARNING: ensure_columns failed — continuing, schema may be incomplete." >&2
    fi

    # Step 2 — Apply any pending Alembic migrations. Safe to run on every deploy;
    # Alembic no-ops if the DB is already at the latest revision(s).
    # This repo has divergent migration heads, so we use `heads` (plural).
    echo "[production] Running database migrations (alembic upgrade heads)..."
    if ! alembic upgrade heads; then
        echo "[production] WARNING: alembic upgrade failed — continuing startup." >&2
    fi

    # Step 3 — Ensure admin user exists (idempotent).
    echo "[production] Ensuring admin user exists..."
    if ! python3 scripts/ensure_admin.py; then
        echo "[production] WARNING: ensure_admin failed — admin user may be missing." >&2
    fi

    # Step 4 — Seed blockchain genesis block if not already present.
    # The genesis block is stored as an IoTEvent row; if it never made it to
    # the DB (e.g. first-deploy race where tables were not ready yet), every
    # subsequent health-check returns False and the kernel stays DEGRADED.
    echo "[production] Seeding blockchain genesis block (idempotent)..."
    if ! python3 scripts/seed_genesis.py; then
        echo "[production] WARNING: seed_genesis failed -- blockchain may stay UNHEALTHY." >&2
    fi
else
    echo "[production] Skipping DB setup (no Postgres DATABASE_URL detected)."
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
