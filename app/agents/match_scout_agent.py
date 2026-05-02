"""app/agents/match_scout_agent.py

MatchScoutAgent — runs every 15 minutes.

Uses Gemini (free tier) to generate pre-match intelligence briefs for
upcoming fixtures that haven't been scouted yet. Results are stored in the
AgentInsight table and broadcast as IoT events so the live dashboard updates.

Free-tier limit protection:
  - Max 3 matches per cycle (Gemini free: 15 RPM / 1M TPD)
  - 2-second pause between API calls
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

MAX_MATCHES_PER_CYCLE = 3


def _build_scout_prompt(home: str, away: str, league: str,
                         home_prob: float, draw_prob: float, away_prob: float) -> str:
    return f"""You are a professional football scout. Write a concise pre-match intelligence brief.

Match: {home} vs {away}
League: {league.replace("_", " ").title()}
ML Probabilities: Home {home_prob*100:.1f}% | Draw {draw_prob*100:.1f}% | Away {away_prob*100:.1f}%

Provide a JSON object (no markdown fences):
{{
  "headline": "one-line summary",
  "home_form": "recent form assessment",
  "away_form": "recent form assessment",
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "tactical_note": "tactical matchup insight",
  "risk_level": "LOW|MEDIUM|HIGH",
  "confidence": 0.0
}}"""



class MatchScoutAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="match-scout",
            interval_seconds=15 * 60,
            initial_delay_seconds=120,
        )
        self._scouted_ids: set[int] = set()

    async def run_cycle(self) -> Dict[str, Any]:

        from app.db.database import AsyncSessionLocal
        from app.db.models import Match, Prediction, AgentInsight
        from app.iot.processor import store_and_broadcast
        from sqlalchemy import select

        now = datetime.now(timezone.utc)
        window_end = now + timedelta(hours=24)

        insights_stored = 0
        matches_scouted: List[str] = []

        async with AsyncSessionLocal() as db:
            rows = await db.execute(
                select(Match, Prediction)
                .outerjoin(Prediction, Prediction.match_id == Match.id)
                .where(
                    Match.kickoff_time >= now,
                    Match.kickoff_time <= window_end,
                    Match.status == "scheduled",
                )
                .limit(20)
            )
            candidates = rows.all()

        unscouted = [
            (m, p) for m, p in candidates
            if m.id not in self._scouted_ids
        ][:MAX_MATCHES_PER_CYCLE]

        for match, pred in unscouted:
            home_prob = pred.home_prob if pred else 0.34
            draw_prob = pred.draw_prob if pred else 0.33
            away_prob = pred.away_prob if pred else 0.33

            prompt = _build_scout_prompt(
                match.home_team, match.away_team,
                match.league or "unknown",
                home_prob, draw_prob, away_prob,
            )

            raw = await call_ai(prompt)
            if not raw:
                continue

            import json as _json
            try:
                text = raw.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                parsed = _json.loads(text.strip())
                content = parsed.get("headline", raw[:300])
                confidence = float(parsed.get("confidence", 0.6))
                meta = parsed
            except Exception:
                content = raw[:500]
                confidence = 0.5
                meta = {}

            async with AsyncSessionLocal() as db:
                insight = AgentInsight(
                    agent_name="match-scout",
                    insight_type="match_scout",
                    match_id=match.id,
                    ai_provider="gemini",
                    content=content,
                    meta=meta,
                    confidence=confidence,
                )
                db.add(insight)
                await db.commit()

            await store_and_broadcast(
                source="agent",
                event_type="ai_signal",
                match_id=match.id,
                payload={
                    "agent":      "match-scout",
                    "match":      f"{match.home_team} vs {match.away_team}",
                    "headline":   content,
                    "confidence": confidence,
                },
            )

            self._scouted_ids.add(match.id)
            matches_scouted.append(f"{match.home_team} vs {match.away_team}")
            insights_stored += 1
            await asyncio.sleep(2)

        logger.info(
            "[match-scout] cycle done: %d scouted, %d total in cache",
            insights_stored, len(self._scouted_ids),
        )
        return {
            "matches_scouted": matches_scouted,
            "insights_stored": insights_stored,
            "scouted_cache_size": len(self._scouted_ids),
        }
