"""app/agents/odds_anomaly_agent.py

OddsAnomalyAgent — runs every 8 minutes.

VIT Self-Contained Intelligence Enhancement:
  Primary detection now uses ML probability drift from the VIT SCIE engine,
  so the agent fires useful anomaly reports even when no market odds are stored
  on Match records.  Market-odds comparison (opening/closing) is retained as a
  supplementary layer when data is available.

Detection modes
---------------
1. SCIE Probability Drift  — compares the ML ensemble's home/draw/away probs
   between consecutive cycles (threshold: 8 % change in any outcome).
   Derives synthetic implied odds via vit_intelligence.synthetic_odds().
2. Market Odds Movement     — uses Match.opening_odds_home / closing_odds_home
   when populated (original behaviour, now secondary).

Free-tier limit protection:
  - Max 2 anomalies explained per cycle (Grok free tier is limited)
  - ML prob snapshots tracked in memory between cycles
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.services.ai_client import call_ai
from app.services.vit_intelligence import detect_probability_drift, synthetic_odds

logger = logging.getLogger(__name__)

MOVEMENT_THRESHOLD       = 0.12   # 12% implied-prob change → market-odds anomaly
PROB_DRIFT_THRESHOLD     = 0.08   # 8% ML-prob shift → SCIE anomaly
MAX_EXPLANATIONS         = 2


def _implied_prob(odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if odds and odds > 1.0:
        return 1.0 / odds
    return 0.33


def _build_anomaly_prompt(home: str, away: str,
                           prev_home: float, curr_home: float,
                           prev_away: float, curr_away: float,
                           source: str = "market") -> str:
    direction = "shortened" if curr_home < prev_home else "drifted"
    source_note = (
        "ML ensemble probability shift" if source == "scie"
        else "market odds movement"
    )
    return f"""You are a sharp sports betting market analyst.

Match: {home} vs {away}

Significant {source_note} detected:
- Home Win odds: {prev_home:.2f} → {curr_home:.2f} ({direction})
- Away Win odds: {prev_away:.2f} → {curr_away:.2f}

In 2-3 concise sentences, explain what market intelligence or news event could
explain this shift. Consider: injury news, lineup leaks, weather,
referee assignment, tactical shifts, or sharp money.

Return ONLY a JSON object (no markdown fences):
{{
  "explanation": "your 2-3 sentence explanation",
  "likely_cause": "INJURY|LINEUP|WEATHER|SHARP_MONEY|REFEREE|UNKNOWN",
  "confidence": 0.0,
  "action": "WATCH|FADE|FOLLOW"
}}"""


async def _call_native(prompt: str) -> str | None:
    """Wrapper kept for backward compat — now uses the shared cascade client."""
    return await call_ai(prompt, max_tokens=400, temperature=0.3)


class OddsAnomalyAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="odds-anomaly",
            interval_seconds=8 * 60,
            initial_delay_seconds=60,
        )
        # Memory stores for drift detection
        self._prev_odds:  Dict[int, Dict] = {}   # market-odds snapshots
        self._prev_probs: Dict[int, Dict] = {}   # ML-prob snapshots (SCIE)

    async def run_cycle(self) -> Dict[str, Any]:
        grok_key = True  # always try — cascade client handles key/availability

        from app.db.database import AsyncSessionLocal
        from app.db.models import Match, Prediction, AgentInsight
        from app.iot.processor import store_and_broadcast
        from sqlalchemy import select

        now    = datetime.now(timezone.utc)
        now_naive = now.replace(tzinfo=None)
        window = now_naive + timedelta(hours=48)

        anomalies_detected: List[Dict] = []
        explained = 0

        # ── Fetch upcoming matches + predictions ──────────────────────────────
        async with AsyncSessionLocal() as db:
            rows = await db.execute(
                select(Match, Prediction)
                .join(Prediction, Prediction.match_id == Match.id)
                .where(
                    Match.kickoff_time >= now_naive,
                    Match.kickoff_time <= window,
                    Match.status == "scheduled",
                )
            )
            pairs = rows.all()

        # ── MODE 1: SCIE Probability Drift ────────────────────────────────────
        curr_probs: Dict[int, Dict] = {}
        for match, pred in pairs:
            if pred and pred.home_prob and pred.draw_prob and pred.away_prob:
                curr_probs[match.id] = {
                    "home_team": match.home_team,
                    "away_team": match.away_team,
                    "home_p":    float(pred.home_prob),
                    "draw_p":    float(pred.draw_prob),
                    "away_p":    float(pred.away_prob),
                }

        scie_anomalies = detect_probability_drift(
            self._prev_probs, curr_probs, threshold=PROB_DRIFT_THRESHOLD
        )
        self._prev_probs = curr_probs

        for a in scie_anomalies:
            anomalies_detected.append({**a, "_source": "scie"})

        # ── MODE 2: Market Odds Movement (supplementary) ─────────────────────
        curr_odds: Dict[int, Dict] = {}
        for match, pred in pairs:
            h = match.opening_odds_home or match.closing_odds_home
            a = match.opening_odds_away or match.closing_odds_away
            if h and a:
                curr_odds[match.id] = {
                    "home_team":  match.home_team,
                    "away_team":  match.away_team,
                    "home_odds":  h,
                    "away_odds":  a,
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
                # Avoid duplicating SCIE anomaly for same match
                if not any(a["match_id"] == match_id for a in anomalies_detected):
                    anomalies_detected.append({
                        "match_id":        match_id,
                        "home_team":       curr["home_team"],
                        "away_team":       curr["away_team"],
                        "home_odds_prev":  prev["home_odds"],
                        "home_odds_curr":  curr["home_odds"],
                        "away_odds_prev":  prev["away_odds"],
                        "away_odds_curr":  curr["away_odds"],
                        "max_move":        round(max(home_move, away_move), 4),
                        "_source":         "market",
                    })

        self._prev_odds = curr_odds

        # ── Explain top anomalies ─────────────────────────────────────────────
        for anomaly in anomalies_detected[:MAX_EXPLANATIONS]:
            source = anomaly.get("_source", "scie")

            # Get odds values regardless of source
            prev_home_odds = anomaly.get("home_odds_prev") or anomaly.get("prev_odds", {}).get("home", 2.0)
            curr_home_odds = anomaly.get("home_odds_curr") or anomaly.get("curr_odds", {}).get("home", 2.0)
            prev_away_odds = anomaly.get("away_odds_prev") or anomaly.get("prev_odds", {}).get("away", 2.0)
            curr_away_odds = anomaly.get("away_odds_curr") or anomaly.get("curr_odds", {}).get("away", 2.0)

            if False:
                explanation = (
                    f"VIT SCIE detected a significant ML probability shift for "
                    f"{anomaly['home_team']} vs {anomaly['away_team']} "
                    f"(max drift: {anomaly.get('max_move',0)*100:.1f}%). "
                    "Grok key not configured for detailed explanation."
                ) if source == "scie" else (
                    "Significant odds movement detected — Grok key not configured for explanation."
                )
                cause = "UNKNOWN"
                confidence = 0.3
                action = "WATCH"
                meta: Dict = {**anomaly}
            else:
                prompt = _build_anomaly_prompt(
                    anomaly["home_team"], anomaly["away_team"],
                    prev_home_odds, curr_home_odds,
                    prev_away_odds, curr_away_odds,
                    source=source,
                )
                raw = await _call_native(prompt)

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
                    # Grok call failed — store a generic report anyway
                    explanation = (
                        f"Probability drift detected for {anomaly['home_team']} vs "
                        f"{anomaly['away_team']} (drift: {anomaly.get('max_move',0)*100:.1f}%). "
                        "Monitor for lineup or injury news."
                    )
                    cause = "UNKNOWN"
                    confidence = 0.4
                    action = "WATCH"
                    meta = {**anomaly}

            async with AsyncSessionLocal() as db:
                insight = AgentInsight(
                    agent_name="odds-anomaly",
                    insight_type="odds_anomaly",
                    match_id=anomaly["match_id"],
                    ai_provider="native",
                    content=explanation,
                    meta={k: v for k, v in meta.items() if not k.startswith("_")},
                    confidence=confidence,
                )
                db.add(insight)
                await db.commit()

            await store_and_broadcast(
                source="agent",
                event_type="odds_change",
                match_id=anomaly["match_id"],
                payload={
                    "agent":       "odds-anomaly",
                    "match":       f"{anomaly['home_team']} vs {anomaly['away_team']}",
                    "cause":       cause,
                    "action":      action,
                    "move":        anomaly.get("max_move", 0),
                    "source":      source,
                    "explanation": explanation,
                },
            )
            explained += 1
            await asyncio.sleep(2)

        logger.info(
            "[odds-anomaly] cycle done: %d matches, scie_anomalies=%d market_anomalies=%d explained=%d",
            len(curr_probs),
            len(scie_anomalies),
            len([a for a in anomalies_detected if a.get("_source") == "market"]),
            explained,
        )
        return {
            "matches_checked":     len(curr_probs),
            "anomalies_detected":  len(anomalies_detected),
            "anomalies_explained": explained,
            "scie_drift_found":    len(scie_anomalies),
            "prob_threshold":      PROB_DRIFT_THRESHOLD,
            "market_threshold":    MOVEMENT_THRESHOLD,
        }
