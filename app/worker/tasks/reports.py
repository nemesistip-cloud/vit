"""app/worker/tasks/reports.py — Celery tasks for analytics report generation."""
from __future__ import annotations

import asyncio
import logging

from app.worker.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="reports.weekly_analytics")
def generate_weekly_analytics():
    """Generate and dispatch weekly analytics report."""
    async def _run():
        from app.agents.analytics_reporter_agent import AnalyticsReporterAgent
        return await AnalyticsReporterAgent().run_cycle()
    return asyncio.run(_run())
