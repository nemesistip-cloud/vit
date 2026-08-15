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
    # init_db.py creates the core tables (users, audit_logs, wallets, etc.) that
    # auth routes depend on.  Run it synchronously BEFORE uvicorn starts so that
    # the very first login/register request never hits a missing table.
    echo "[production] Running DB table bootstrap (init_db.py) — blocking until complete..."
    python3 scripts/init_db.py \
      || echo "[production] WARNING: init_db failed — schema may be incomplete." >&2

    # Non-critical steps: run in background so uvicorn binds immediately after.
    (
      echo "[production] [bg] Running pre-flight schema guard (ensure_columns.py)..."
      python3 scripts/ensure_columns.py \
        || echo "[production] [bg] WARNING: ensure_columns failed." >&2

      echo "[production] [bg] Running production-safe migrations (run_migrations.py)..."
      if python3 scripts/run_migrations.py; then
          echo "[production] [bg] Migrations (alembic upgrade heads) completed successfully."
      else
          echo "[production] [bg] ERROR: run_migrations.py failed — check logs above." >&2
      fi

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
