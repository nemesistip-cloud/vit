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
    # All subsequent, non-critical steps run in the background to keep startup fast.
    echo "[production] Running DB table bootstrap (init_db.py) — blocking until complete..."
    python3 scripts/init_db.py \
      || echo "[production] WARNING: init_db failed — schema may be incomplete." >&2

    # Non-critical steps: run in background so uvicorn binds immediately after.
    (
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
    echo "[production] Background DB tasks started (PID: $!) — uvicorn binding now."
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
