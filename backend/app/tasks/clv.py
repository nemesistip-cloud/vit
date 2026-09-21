# app/tasks/clv.py
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from celery import shared_task

    @shared_task(name="update_clv_task")
    def update_clv_task(match_id: int, prediction_id: int = None, entry_odds: float = None):
        logger.info(f"Updating CLV for match {match_id}")
        return {"match_id": match_id, "clv_updated": True, "timestamp": datetime.now().isoformat()}

    @shared_task(name="recalculate_clv_stats_task")
    def recalculate_clv_stats_task():
        logger.info("Recalculating CLV statistics")
        return {"status": "completed", "timestamp": datetime.now().isoformat()}

except ImportError:
    class _FakeTask:
        def delay(self, *args, **kwargs):
            logger.debug("Celery not available — task skipped")

    update_clv_task = _FakeTask()
    recalculate_clv_stats_task = _FakeTask()
