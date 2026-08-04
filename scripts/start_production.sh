#!/usr/bin/env bash
# scripts/start_production.sh — production startup for Render (Python runtime, free plan)
# Starts uvicorn immediately so health checks pass, then runs DB setup in background.
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:."
PORT="${PORT:-8000}"

echo "[production] VIT Network startup — port ${PORT}"

# ── Background DB setup ────────────────────────────────────────────────────────
DATABASE_URL="${DATABASE_URL:-}"
if [[ "${DATABASE_URL}" == *"postgres"* ]]; then
    (
      echo "[production] [bg] Starting DB setup..."

      echo "[production] [bg] Running DB table bootstrap (init_db.py)..."
      python3 scripts/init_db.py \
        || echo "[production] [bg] WARNING: init_db failed — continuing." >&2

      echo "[production] [bg] Running pre-flight schema guard (ensure_columns.py)..."
      python3 scripts/ensure_columns.py \
        || echo "[production] [bg] WARNING: ensure_columns failed — schema may be incomplete." >&2

      echo "[production] [bg] Running production-safe migrations (run_migrations.py)..."
      if python3 scripts/run_migrations.py; then
          echo "[production] [bg] Migrations completed successfully."
      else
          echo "[production] [bg] ERROR: run_migrations.py failed — schema may be incomplete. Check logs above." >&2
      fi

      echo "[production] [bg] Ensuring admin user exists..."
      python3 scripts/ensure_admin.py \
        || echo "[production] [bg] WARNING: ensure_admin failed — admin user may be missing." >&2

      echo "[production] [bg] Seeding blockchain genesis block (idempotent)..."
      python3 scripts/seed_genesis.py \
        || echo "[production] [bg] WARNING: seed_genesis failed — blockchain may stay UNHEALTHY." >&2

      echo "[production] [bg] DB setup complete."
    ) &
    echo "[production] DB setup started in background (PID: $!) — uvicorn binding now."
else
    echo "[production] Skipping DB setup (no Postgres DATABASE_URL detected)."
fi

# ── Start FastAPI immediately ──────────────────────────────────────────────────
# uvicorn binds to PORT right away so Render health checks pass within timeout.
# The kernel's DatabaseSubsystem handles schema verification at runtime.
echo "[production] Starting VIT Network on port ${PORT}..."
exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --timeout-keep-alive 75 \
    --log-level info
