# app/tasks/odds.py
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from celery import shared_task

    @shared_task(name="fetch_odds_task")
    def fetch_odds_task(match_id: int):
        logger.info(f"Fetching odds for match {match_id}")
        return {"match_id": match_id, "status": "completed", "timestamp": datetime.now().isoformat()}

    @shared_task(name="fetch_batch_odds_task")
    def fetch_batch_odds_task(match_ids: list):
        results = []
        for match_id in match_ids:
            result = fetch_odds_task.delay(match_id)
            results.append(result.id)
        return {"batch_size": len(match_ids), "task_ids": results}

except ImportError:
    class _FakeTask:
        def delay(self, *args, **kwargs):
            logger.debug("Celery not available — task skipped")

    fetch_odds_task = _FakeTask()
    fetch_batch_odds_task = _FakeTask()
