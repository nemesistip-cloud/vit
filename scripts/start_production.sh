#!/usr/bin/env bash
# scripts/start_production.sh — production startup for Render (Python runtime, free plan)
# Starts uvicorn immediately so health checks pass, then runs DB setup in background.
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:."
PORT="${PORT:-8000}"

echo "[production] VIT Network startup — port ${PORT}"

# ── DB setup ──────────────────────────────────────────────────────────────────
DATABASE_URL="${DATABASE_URL:-}"
if [[ "${DATABASE_URL}" == *"postgres"* ]]; then
    # Run DB setup asynchronously in background so uvicorn binds immediately and
    # Render port scan never times out waiting for remote DB connection/lock.
    (
      echo "[production] [bg] Running DB table bootstrap (init_db.py)..."
      python3 scripts/init_db.py \
        || echo "[production] [bg] WARNING: init_db failed — schema may be incomplete." >&2

      echo "[production] [bg] Running pre-flight schema guard (ensure_columns.py)..."
      python3 scripts/ensure_columns.py \
        || echo "[production] [bg] WARNING: ensure_columns failed." >&2

      echo "[production] [bg] Running production-safe migrations (run_migrations.py)..."
      python3 scripts/run_migrations.py \
        || echo "[production] [bg] WARNING: migrations failed." >&2

      # ── Fresh-start user reset ─────────────────────────────────────────────
      # Only executes when RESET_USERS_ON_BOOT=true.
      # Clears all user accounts so a fresh admin can be created below.
      echo "[production] [bg] Checking user reset flag (RESET_USERS_ON_BOOT)..."
      python3 scripts/reset_users.py \
        || echo "[production] [bg] WARNING: reset_users failed — existing users retained." >&2

      echo "[production] [bg] Ensuring admin user exists..."
      python3 scripts/ensure_admin.py \
        || echo "[production] [bg] WARNING: ensure_admin failed — admin user may be missing." >&2

      echo "[production] [bg] Seeding match predictions..."
      python3 scripts/seed_predictions.py \
        || echo "[production] [bg] WARNING: seed_predictions failed." >&2

      echo "[production] [bg] Seeding blockchain genesis block (idempotent)..."
      python3 scripts/seed_genesis.py \
        || echo "[production] [bg] WARNING: seed_genesis failed — blockchain may stay UNHEALTHY." >&2

      echo "[production] [bg] DB setup complete."
    ) &
    echo "[production] Background DB tasks started (PID: $!) — uvicorn binding now."
else
    echo "[production] Skipping DB setup (no Postgres DATABASE_URL detected)."
fi

# ── Start FastAPI immediately ──────────────────────────────────────────────────
echo "[production] Starting VIT Network on port ${PORT}..."
exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --timeout-keep-alive 75 \
    --log-level info
