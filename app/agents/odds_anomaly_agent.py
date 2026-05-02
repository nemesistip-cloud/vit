"""app/agents/odds_anomaly_agent.py

OddsAnomalyAgent — runs every 8 minutes.

Scans all stored predictions for odds movements above a threshold between
consecutive cycles. When an anomaly is detected, uses Grok (free tier via
xAI) to generate a plain-language explanation. Results stored in
AgentInsight + broadcast as IoT events.

Free-tier limit protection:
  - Max 2 anomalies explained per cycle (Grok free tier is limited)
  - Tracks previous cycle odds in memory (no extra DB reads)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

MOVEMENT_THRESHOLD = 0.12   # 12% change in implied probability triggers anomaly
MAX_EXPLANATIONS   = 2


def _implied_prob(odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if odds and odds > 1.0:
        return 1.0 / odds
    return 0.33


def _build_anomaly_prompt(home: str, away: str,
                           prev_home: float, curr_home: float,
                           prev_away: float, curr_away: float) -> str:
    direction = "shortened" if curr_home < prev_home else "drifted"
    return f"""You are a sharp sports betting market analyst.

Match: {home} vs {away}

Odds movement detected:
- Home Win odds: {prev_home:.2f} → {curr_home:.2f} ({direction})
- Away Win odds: {prev_away:.2f} → {curr_away:.2f}

In 2-3 concise sentences, explain what market intelligence or news event could
explain this odds movement. Consider: injury news, lineup leaks, weather, 
referee assignment, tactical shifts, or sharp money.

Return ONLY a JSON object (no markdown fences):
{{
  "explanation": "your 2-3 sentence explanation",
  "likely_cause": "INJURY|LINEUP|WEATHER|SHARP_MONEY|REFEREE|UNKNOWN",
  "confidence": 0.0,
  "action": "WATCH|FADE|FOLLOW"
}}"""


async def _call_grok(prompt: str, api_key: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-beta",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 400,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("[odds-anomaly] Grok call failed: %s", e)
        return None


class OddsAnomalyAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="odds-anomaly",
            interval_seconds=8 * 60,
            initial_delay_seconds=60,
        )
        self._prev_odds: Dict[int, Dict] = {}   # match_id → {home_odds, away_odds}

    async def run_cycle(self) -> Dict[str, Any]:
        grok_key = os.getenv("XAI_API_KEY", "").strip()

        from app.db.database import AsyncSessionLocal
        from app.db.models import Match, Prediction, AgentInsight
        from app.iot.processor import store_and_broadcast
        from sqlalchemy import select
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        window = now + timedelta(hours=48)

        anomalies_detected: List[Dict] = []
        explained = 0

        async with AsyncSessionLocal() as db:
            rows = await db.execute(
                select(Match, Prediction)
                .join(Prediction, Prediction.match_id == Match.id)
                .where(
                    Match.kickoff_time >= now,
                    Match.kickoff_time <= window,
                    Match.status == "scheduled",
                )
            )
            pairs = rows.all()

        curr_odds: Dict[int, Dict] = {}
        for match, pred in pairs:
            if pred.home_odds and pred.away_odds:
                curr_odds[match.id] = {
                    "home_team":  match.home_team,
                    "away_team":  match.away_team,
                    "home_odds":  pred.home_odds,
                    "away_odds":  pred.away_odds,
                    "match_id":   match.id,
                }

        for match_id, curr in curr_odds.items():
            prev = self._prev_odds.get(match_id)
            if not prev:
                continue

            home_prev_prob = _implied_prob(prev["home_odds"])
            home_curr_prob = _implied_prob(curr["home_odds"])
            away_prev_prob = _implied_prob(prev["away_odds"])
            away_curr_prob = _implied_prob(curr["away_odds"])

            home_move = abs(home_curr_prob - home_prev_prob)
            away_move = abs(away_curr_prob - away_prev_prob)

            if max(home_move, away_move) >= MOVEMENT_THRESHOLD:
                anomalies_detected.append({
                    "match_id":  match_id,
                    "home_team": curr["home_team"],
                    "away_team": curr["away_team"],
                    "home_odds_prev": prev["home_odds"],
                    "home_odds_curr": curr["home_odds"],
                    "away_odds_prev": prev["away_odds"],
                    "away_odds_curr": curr["away_odds"],
                    "max_move": round(max(home_move, away_move), 4),
                })

        self._prev_odds = curr_odds

        for anomaly in anomalies_detected[:MAX_EXPLANATIONS]:
            if not grok_key:
                explanation = "Significant odds movement detected — Grok key not configured for explanation."
                cause = "UNKNOWN"
                confidence = 0.3
                action = "WATCH"
                meta: Dict = {**anomaly}
            else:
                prompt = _build_anomaly_prompt(
                    anomaly["home_team"], anomaly["away_team"],
                    anomaly["home_odds_prev"], anomaly["home_odds_curr"],
                    anomaly["away_odds_prev"], anomaly["away_odds_curr"],
                )
                raw = await _call_grok(prompt, grok_key)

                if raw:
                    import json as _json
                    try:
                        text = raw.strip()
                        if text.startswith("```"):
                            text = text.split("```")[1]
                            if text.startswith("json"):
                                text = text[4:]
                        parsed = _json.loads(text.strip())
                        explanation = parsed.get("explanation", raw[:300])
                        cause = parsed.get("likely_cause", "UNKNOWN")
                        confidence = float(parsed.get("confidence", 0.55))
                        action = parsed.get("action", "WATCH")
                        meta = {**anomaly, **parsed}
                    except Exception:
                        explanation = raw[:500]
                        cause = "UNKNOWN"
                        confidence = 0.5
                        action = "WATCH"
                        meta = {**anomaly}
                else:
                    continue

            async with AsyncSessionLocal() as db:
                insight = AgentInsight(
                    agent_name="odds-anomaly",
                    insight_type="odds_anomaly",
                    match_id=anomaly["match_id"],
                    ai_provider="grok" if grok_key else "none",
                    content=explanation,
                    meta=meta,
                    confidence=confidence,
                )
                db.add(insight)
                await db.commit()

            await store_and_broadcast(
                source="agent",
                event_type="odds_change",
                match_id=anomaly["match_id"],
                payload={
                    "agent":      "odds-anomaly",
                    "match":      f"{anomaly['home_team']} vs {anomaly['away_team']}",
                    "cause":      cause,
                    "action":     action,
                    "move":       anomaly["max_move"],
                    "explanation": explanation,
                },
            )
            explained += 1
            await asyncio.sleep(2)

        logger.info(
            "[odds-anomaly] cycle done: %d matches checked, %d anomalies, %d explained",
            len(curr_odds), len(anomalies_detected), explained,
        )
        return {
            "matches_checked":     len(curr_odds),
            "anomalies_detected":  len(anomalies_detected),
            "anomalies_explained": explained,
            "threshold":           MOVEMENT_THRESHOLD,
        }
