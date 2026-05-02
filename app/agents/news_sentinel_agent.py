"""app/agents/news_sentinel_agent.py

NewsSentinelAgent — runs every 20 minutes.

Scrapes latest injuries via Transfermarkt, groups them by team, then for
each team with ≥1 injury uses Gemini (free tier) to assess the impact on
upcoming matches. Results stored in AgentInsight + broadcast as IoT events.

Free-tier limit protection:
  - Max 3 teams per cycle
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

MAX_TEAMS_PER_CYCLE = 3


def _build_news_prompt(team: str, injuries: List[Dict]) -> str:
    injury_lines = "\n".join(
        f"- {inj.get('player_name', 'Unknown')} ({inj.get('injury', 'injury')}, "
        f"status: {inj.get('status', 'unknown')})"
        for inj in injuries[:6]
    )
    return f"""You are a football injury analyst. Assess the impact of the following absences on {team}.

Current absences for {team}:
{injury_lines}

Return ONLY a JSON object (no markdown fences):
{{
  "team": "{team}",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "summary": "2-sentence impact assessment",
  "key_positions_affected": ["position1", "position2"],
  "betting_implication": "1 sentence on how this shifts the team's match odds",
  "confidence": 0.0
}}"""



class NewsSentinelAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="news-sentinel",
            interval_seconds=20 * 60,
            initial_delay_seconds=150,
        )

    async def run_cycle(self) -> Dict[str, Any]:

        from app.services.scraper import InjuryScraper
        from app.db.database import AsyncSessionLocal
        from app.db.models import AgentInsight
        from app.iot.processor import store_and_broadcast

        scraper = InjuryScraper()
        try:
            all_injuries = await scraper.fetch_all_injuries()
        except Exception as e:
            logger.warning("[news-sentinel] scraper failed: %s", e)
            all_injuries = []

        if not all_injuries:
            return {"teams_analyzed": 0, "insights_stored": 0, "injuries_found": 0}

        team_map: Dict[str, List[Dict]] = {}
        for inj in all_injuries:
            team = inj.get("team", "Unknown")
            if team and team != "Unknown":
                team_map.setdefault(team, []).append(inj)

        high_impact_teams = sorted(
            team_map.items(), key=lambda x: len(x[1]), reverse=True
        )[:MAX_TEAMS_PER_CYCLE]

        insights_stored = 0
        teams_analyzed: List[str] = []

        for team, injuries in high_impact_teams:
            prompt = _build_news_prompt(team, injuries)
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
                content = parsed.get("summary", raw[:300])
                confidence = float(parsed.get("confidence", 0.65))
                meta = {**parsed, "injury_count": len(injuries)}
            except Exception:
                content = raw[:500]
                confidence = 0.5
                meta = {"injury_count": len(injuries)}

            async with AsyncSessionLocal() as db:
                insight = AgentInsight(
                    agent_name="news-sentinel",
                    insight_type="team_news",
                    match_id=None,
                    team=team,
                    ai_provider="gemini",
                    content=content,
                    meta=meta,
                    confidence=confidence,
                )
                db.add(insight)
                await db.commit()

            await store_and_broadcast(
                source="agent",
                event_type="injury_update",
                match_id=None,
                payload={
                    "agent":    "news-sentinel",
                    "team":     team,
                    "severity": meta.get("severity", "UNKNOWN"),
                    "summary":  content,
                    "injuries": len(injuries),
                },
            )

            teams_analyzed.append(team)
            insights_stored += 1
            await asyncio.sleep(2)

        logger.info(
            "[news-sentinel] cycle done: %d teams analyzed, %d total injuries",
            insights_stored, len(all_injuries),
        )
        return {
            "teams_analyzed":  teams_analyzed,
            "insights_stored": insights_stored,
            "injuries_found":  len(all_injuries),
        }
