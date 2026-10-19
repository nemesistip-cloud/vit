"""Scheduled importer for provider-backed fixtures across tracked sports."""

from __future__ import annotations

from typing import Any, Dict

from app.agents.base import BaseAgent


class FixtureSyncAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="fixture-sync",
            interval_seconds=6 * 60 * 60,
            initial_delay_seconds=45,
        )

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.services.sportsdb_api import sync_upcoming_fixtures

        async with AsyncSessionLocal() as db:
            result = await sync_upcoming_fixtures(db, days_ahead=60)
        return {"status": "ok", **result}