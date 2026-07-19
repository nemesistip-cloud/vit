#!/usr/bin/env bash
# Production startup — FastAPI + Integrated Background Agents.
# DB setup runs in background so uvicorn binds immediately and passes Render health checks.
set -euo pipefail
cd "$(dirname "$0")/.."

# PORT: read from env (Render dashboard sets PORT=8000).
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

# ── DB setup runs in background ────────────────────────────────────────────────
# Running synchronously before uvicorn caused Render health-check timeouts
# (~80s of DB scripts before uvicorn even binds).  Moving to background lets
# uvicorn respond to /ping immediately while schema work completes in parallel.
# Every step is idempotent so concurrent access with kernel startup is safe.
if [ -n "${DATABASE_URL:-}" ] && echo "${DATABASE_URL}" | grep -q "postgres"; then
    (
      set +e   # individual step failures must not kill this subshell

      echo "[production] [bg] Running DB table bootstrap (init_db.py)..."
      python3 scripts/init_db.py \
        || echo "[production] [bg] WARNING: init_db failed — continuing." >&2

      echo "[production] [bg] Running pre-flight schema guard (ensure_columns.py)..."
      python3 scripts/ensure_columns.py \
        || echo "[production] [bg] WARNING: ensure_columns failed — schema may be incomplete." >&2

      # Alembic: stamp fresh DBs, upgrade existing ones.
      echo "[production] [bg] Checking Alembic migration state..."
      _ALEMBIC_ACTION=$(python3 - <<'PYEOF'
import os, sys
from sqlalchemy import create_engine, text, inspect as sa_inspect

raw_url = os.environ.get("DATABASE_URL", "")
sync_url = raw_url
for old, new in [
    ("postgresql+asyncpg://", "postgresql://"),
    ("postgres+asyncpg://",   "postgresql://"),
    ("postgres://",           "postgresql://"),
]:
    if sync_url.startswith(old):
        sync_url = new + sync_url[len(old):]
        break

try:
    engine = create_engine(sync_url, connect_args={"connect_timeout": 10})
    with engine.connect() as conn:
        ins = sa_inspect(engine)
        if not ins.has_table("alembic_version"):
            print("STAMP")
        else:
            count = conn.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar()
            print("STAMP" if count == 0 else "UPGRADE")
    engine.dispose()
except Exception as exc:
    print(f"[production] [bg] alembic-check warning: {exc}", file=sys.stderr)
    print("STAMP")
PYEOF
      )

      if [ "${_ALEMBIC_ACTION:-STAMP}" = "STAMP" ]; then
          echo "[production] [bg] Fresh DB (alembic_version absent or empty) — stamping all heads..."
          alembic stamp heads 2>&1 \
            || echo "[production] [bg] WARNING: alembic stamp heads failed — app started without migration tracking." >&2
      else
          echo "[production] [bg] Running pending migrations (alembic upgrade heads)..."
          alembic upgrade heads 2>&1 \
            || echo "[production] [bg] WARNING: alembic upgrade heads failed — schema may be incomplete." >&2
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
