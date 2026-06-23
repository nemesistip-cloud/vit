#!/usr/bin/env bash
# VIT Worker — Celery worker + beat scheduler for autonomous agents.
# Runs as a separate Render Background Worker service (vit-worker).
# REDIS_URL is used as broker and result backend.
set -euo pipefail
cd "$(dirname "$0")/.."

export ENVIRONMENT="${ENVIRONMENT:-production}"
export WORKER_MODE="true"
export USE_REAL_ML_MODELS="${USE_REAL_ML_MODELS:-false}"
export ML_MODEL_CACHE_ENABLED="${ML_MODEL_CACHE_ENABLED:-false}"
export PYTHONPATH="${PYTHONPATH:-}:."

echo "VIT Worker starting..."
echo "  Broker:      ${REDIS_URL:-redis://localhost:6379/0}"
echo "  Concurrency: 2 | Max mem/child: 300MB | Beat: enabled"

exec celery -A app.worker.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --max-memory-per-child=300000 \
  -B \
  --scheduler=celery.beat.PersistentScheduler \
  --beat-schedule=/tmp/celerybeat-schedule
