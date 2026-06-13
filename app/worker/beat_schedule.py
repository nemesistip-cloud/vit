"""app/worker/beat_schedule.py — Celery Beat periodic task schedule.

All hours in Africa/Lagos (UTC+1).
"""
from __future__ import annotations

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "prediction-agent-every-5min": {
        "task": "agents.run_prediction",
        "schedule": 300,
        "options": {"expires": 240},
    },
    "oracle-sentinel-every-minute": {
        "task": "agents.oracle_sentinel",
        "schedule": 60,
        "options": {"expires": 50},
    },
    "market-scout-every-10min": {
        "task": "agents.market_scout",
        "schedule": 600,
        "options": {"expires": 540},
    },
    "merit-calculator-daily": {
        "task": "agents.merit_calculator",
        "schedule": crontab(hour=1, minute=0),  # 2am Lagos = 1am UTC
        "options": {"expires": 3600},
    },
    "fraud-review-every-15min": {
        "task": "agents.fraud_review",
        "schedule": 900,
        "options": {"expires": 840},
    },
    "withdrawal-gate-every-5min": {
        "task": "agents.withdrawal_gate",
        "schedule": 300,
        "options": {"expires": 240},
    },
    "audit-sentinel-every-30min": {
        "task": "agents.audit_sentinel",
        "schedule": 1800,
        "options": {"expires": 1680},
    },
    "tachyon-health-hourly": {
        "task": "agents.tachyon_health",
        "schedule": 3600,
        "options": {"expires": 3540},
    },
    "evict-stale-models-every-10min": {
        "task": "ml.evict_stale_models",
        "schedule": 600,
        "options": {"expires": 540},
    },
}
