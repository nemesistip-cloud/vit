"""app/agents/match_scout_agent.py — v2: Enhanced Pre-Match & Live Intelligence

Runs every 10 minutes. Two modes:
  PRE-MATCH  — AI brief for upcoming fixtures (48h window), 5 matches/cycle
  LIVE       — Real-time tactical updates for matches currently in progress

Free-tier limit protection:
  - Max 5 analyses per cycle
  - 2-second pause between AI calls
  - Scouted ID cache resets daily to allow re-analysis
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

MAX_PER_CYCLE = 5


def _pre_match_prompt(home: str, away: str, league: str,
                      home_prob: float, draw_prob: float, away_prob: float,
                      kickoff_iso: str) -> str:
    return f"""You are an elite football scout. Write a detailed pre-match intelligence brief.

Match: {home} vs {away}
League: {league.replace("_", " ").title()}
Kickoff: {kickoff_iso[:16]} UTC
ML Ensemble: Home {home_prob*100:.1f}% | Draw {draw_prob*100:.1f}% | Away {away_prob*100:.1f}%

Return ONLY a JSON object (no markdown fences, no extra text):
{{
  "headline": "one punchy line summarising the key narrative",
  "home_form": "3-sentence form assessment",
  "away_form": "3-sentence form assessment",
  "key_factors": ["factor 1", "factor 2", "factor 3", "factor 4"],
  "tactical_note": "2-sentence tactical matchup insight",
  "value_pick": "specific bet recommendation with brief justification",
  "risk_level": "LOW|MEDIUM|HIGH",
  "confidence": 0.0
}}"""


def _live_prompt(home: str, away: str, league: str,
                 home_score: int, away_score: int, minute: int,
                 home_prob: float, away_prob: float) -> str:
    return f"""You are a live football analyst. Provide a real-time match update.

Match: {home} {home_score}-{away_score} {away} ({minute}')
League: {league.replace("_", " ").title()}
Pre-match ML: Home {home_prob*100:.1f}% | Away {away_prob*100:.1f}%

Return ONLY a JSON object (no markdown fences):
{{
  "headline": "current match narrative in one sentence",
  "momentum": "HOME|AWAY|BALANCED",
  "live_analysis": "2-sentence tactical assessment of what's happening",
  "key_factors": ["observation 1", "observation 2"],
  "in_play_bet": "best current in-play opportunity or NONE",
  "revised_home_prob": 0.0,
  "revised_away_prob": 0.0,
  "confidence": 0.0
}}"""


def _parse_ai(raw: str, fallback: str = "") -> Tuple[str, float, dict]:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    try:
        parsed = _json.loads(text.strip())
        content = parsed.get("headline", fallback or raw[:300])
        confidence = float(parsed.get("confidence", 0.6))
        return content, confidence, parsed
    except Exception:
        return raw[:500], 0.5, {}


class MatchScoutAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="match-scout",
            interval_seconds=10 * 60,
            initial_delay_seconds=90,
        )
        self._scouted_ids: set[int] = set()
        self._scouted_date: Optional[str] = None

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.db.models import Match, Prediction, AgentInsight
        from app.iot.processor import store_and_broadcast
        from sqlalchemy import select

        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")

        # Reset scouted cache daily for re-analysis
        if self._scouted_date != today:
            self._scouted_ids.clear()
            self._scouted_date = today

        window_end = now + timedelta(hours=48)
        live_cutoff = now - timedelta(hours=2, minutes=30)

        insights_stored = 0
        pre_match_done: List[str] = []
        live_done: List[str] = []

        async with AsyncSessionLocal() as db:
            # --- PRE-MATCH: upcoming matches in next 48h ---
            rows = await db.execute(
                select(Match, Prediction)
                .outerjoin(Prediction, Prediction.match_id == Match.id)
                .where(
                    Match.kickoff_time >= now,
                    Match.kickoff_time <= window_end,
                    Match.status.in_(["scheduled", "upcoming"]),
                )
                .order_by(Match.kickoff_time.asc())
                .limit(30)
            )
            upcoming = rows.all()

            # --- LIVE: matches currently in progress ---
            live_rows = await db.execute(
                select(Match, Prediction)
                .outerjoin(Prediction, Prediction.match_id == Match.id)
                .where(
                    Match.status.in_(["live", "in_play"]),
                    Match.actual_outcome.is_(None),
                )
                .limit(10)
            )
            live_matches = live_rows.all()

        # Prioritise live matches, then unscouted upcoming
        unscouted_upcoming = [
            (m, p) for m, p in upcoming if m.id not in self._scouted_ids
        ]

        # Combined list: live first, then upcoming, capped at MAX_PER_CYCLE
        to_process: List[Tuple[Match, Optional[Prediction], str]] = []
        for m, p in live_matches[:2]:
            to_process.append((m, p, "live"))
        for m, p in unscouted_upcoming[:MAX_PER_CYCLE - len(to_process)]:
            to_process.append((m, p, "pre"))

        for match, pred, mode in to_process:
            home_prob = pred.home_prob if pred else 0.34
            draw_prob = pred.draw_prob if pred else 0.33
            away_prob = pred.away_prob if pred else 0.33

            if mode == "live":
                h_score = match.home_goals or 0
                a_score = match.away_goals or 0
                minute = 45  # default; live tracker updates this
                prompt = _live_prompt(
                    match.home_team, match.away_team,
                    match.league or "unknown",
                    h_score, a_score, minute,
                    home_prob, away_prob,
                )
                insight_type = "live_update"
            else:
                ko = match.kickoff_time.isoformat() if match.kickoff_time else "unknown"
                prompt = _pre_match_prompt(
                    match.home_team, match.away_team,
                    match.league or "unknown",
                    home_prob, draw_prob, away_prob, ko,
                )
                insight_type = "match_scout"

            raw = await call_ai(prompt, max_tokens=500)
            if not raw:
                continue

            content, confidence, meta = _parse_ai(raw)

            async with AsyncSessionLocal() as db:
                insight = AgentInsight(
                    agent_name="match-scout",
                    insight_type=insight_type,
                    match_id=match.id,
                    ai_provider="multi",
                    content=content,
                    meta={**meta, "mode": mode, "match": f"{match.home_team} vs {match.away_team}"},
                    confidence=confidence,
                )
                db.add(insight)
                await db.commit()

            await store_and_broadcast(
                source="agent",
                event_type="ai_signal",
                match_id=match.id,
                payload={
                    "agent":       "match-scout",
                    "mode":        mode,
                    "match":       f"{match.home_team} vs {match.away_team}",
                    "headline":    content,
                    "risk_level":  meta.get("risk_level", "MEDIUM"),
                    "confidence":  confidence,
                    "value_pick":  meta.get("value_pick") or meta.get("in_play_bet"),
                },
            )

            if mode == "live":
                live_done.append(f"{match.home_team} vs {match.away_team}")
            else:
                self._scouted_ids.add(match.id)
                pre_match_done.append(f"{match.home_team} vs {match.away_team}")

            insights_stored += 1
            await asyncio.sleep(2)

        logger.info(
            "[match-scout] pre=%d live=%d total_cache=%d",
            len(pre_match_done), len(live_done), len(self._scouted_ids),
        )
        return {
            "pre_match_scouted": pre_match_done,
            "live_updated":      live_done,
            "insights_stored":   insights_stored,
            "scouted_cache":     len(self._scouted_ids),
        }
