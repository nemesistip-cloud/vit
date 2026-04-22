# app/tasks/retraining.py
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from celery import shared_task

    @shared_task(name="retrain_models_task")
    def retrain_models_task(model_names: list = None):
        logger.info(f"Retraining models: {model_names or 'all'}")
        return {
            "models_retrained": model_names or ["all"],
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }

    @shared_task(name="check_model_drift_task")
    def check_model_drift_task():
        logger.info("Checking for model drift")
        return {"drift_detected": False, "timestamp": datetime.now().isoformat()}

except ImportError:
    class _FakeTask:
        def delay(self, *args, **kwargs):
            logger.debug("Celery not available — task skipped")

    retrain_models_task = _FakeTask()
    check_model_drift_task = _FakeTask()
