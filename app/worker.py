# app/worker.py
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "")

_celery_available = False
celery_app = None

# Only initialise Celery when a real broker URL is configured.
# In-memory fallback ("memory://") and missing URLs are skipped silently
# so the app starts without Redis/Celery.
if REDIS_URL and not REDIS_URL.startswith("memory://"):
    try:
        from celery import Celery

        celery_app = Celery(
            "vit_worker",
            broker=REDIS_URL,
            backend=REDIS_URL,
            include=["app.tasks"],
        )

        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=30 * 60,
            task_soft_time_limit=25 * 60,
            worker_prefetch_multiplier=1,
            task_acks_late=True,
        )

        _celery_available = True
    except Exception as exc:  # pragma: no cover
        import logging
        logging.getLogger(__name__).warning("Celery unavailable: %s", exc)

if __name__ == "__main__":
    if celery_app:
        celery_app.start()
    else:
        print("No Redis URL configured — Celery worker not started.")
