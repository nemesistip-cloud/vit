"""app/worker/celery_app.py — VIT Network Celery application.

Broker and result backend both use REDIS_URL.

Start the worker with scripts/start_worker.sh:
  celery -A app.worker.celery_app worker --loglevel=info --concurrency=2 -B
"""
from __future__ import annotations

import os
from celery import Celery

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "vit_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.worker.tasks.agents",
        "app.worker.tasks.ml",
        "app.worker.tasks.reports",
        "app.worker.tasks.tachyon",
    ],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Africa/Lagos",
    enable_utc=True,
    worker_max_memory_per_child=300_000,   # 300 MB — recycle worker after this
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,          # one task at a time per worker
    task_track_started=True,
    result_expires=3600,
)

from app.worker.beat_schedule import CELERYBEAT_SCHEDULE  # noqa: E402
celery.conf.beat_schedule = CELERYBEAT_SCHEDULE
