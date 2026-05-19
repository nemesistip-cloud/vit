# app/tasks/__init__.py
"""Celery Tasks Package"""

from app.tasks.odds import fetch_odds_task
from app.tasks.clv import update_clv_task
from app.tasks.retraining import retrain_models_task

__all__ = [
    "fetch_odds_task",
    "update_clv_task", 
    "retrain_models_task"
]