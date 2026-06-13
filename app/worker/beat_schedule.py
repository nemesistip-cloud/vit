"""app/worker/beat_schedule.py — Celery Beat schedule.  Africa/Lagos timezone."""
from __future__ import annotations
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # ── Agent tasks ────────────────────────────────────────────────────────
    "prediction-agent-every-5min":  {"task": "agents.run_prediction",  "schedule": 300,  "options": {"expires": 240}},
    "oracle-sentinel-every-minute": {"task": "agents.oracle_sentinel",  "schedule": 60,   "options": {"expires": 50}},
    "market-scout-every-10min":     {"task": "agents.market_scout",     "schedule": 600,  "options": {"expires": 540}},
    "merit-calculator-daily":       {"task": "agents.merit_calculator", "schedule": crontab(hour=1,  minute=0)},
    "fraud-review-every-15min":     {"task": "agents.fraud_review",     "schedule": 900,  "options": {"expires": 840}},
    "withdrawal-gate-every-5min":   {"task": "agents.withdrawal_gate",  "schedule": 300,  "options": {"expires": 240}},
    "audit-sentinel-every-30min":   {"task": "agents.audit_sentinel",   "schedule": 1800, "options": {"expires": 1680}},
    "tachyon-health-hourly":        {"task": "agents.tachyon_health",   "schedule": 3600, "options": {"expires": 3540}},
    # ── ML tasks ───────────────────────────────────────────────────────────
    "evict-stale-models-every-10min": {"task": "ml.evict_stale_models",    "schedule": 600,  "options": {"expires": 540}},
    "retrain-from-settled-daily":     {"task": "ml.retrain_from_settled",  "schedule": crontab(hour=3, minute=30)},
    "evaluate-models-daily":          {"task": "ml.evaluate_models",       "schedule": crontab(hour=4, minute=0)},
    # ── Report tasks ───────────────────────────────────────────────────────
    "daily-summary-report":    {"task": "reports.daily_summary",          "schedule": crontab(hour=6, minute=0)},
    "weekly-model-accuracy":   {"task": "reports.weekly_model_accuracy",  "schedule": crontab(day_of_week=1, hour=5, minute=0)},
    # ── Tachyon tasks ──────────────────────────────────────────────────────
    "tachyon-health-check":    {"task": "tachyon.health_check", "schedule": 3600, "options": {"expires": 3540}},
    "tachyon-gc-orphans":      {"task": "tachyon.gc_orphans",   "schedule": crontab(hour=2, minute=0)},
}
