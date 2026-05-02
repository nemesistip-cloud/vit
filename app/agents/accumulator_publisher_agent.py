"""app/agents/accumulator_publisher_agent.py  — Item 9: Accumulator Auto-Publisher

Runs every 2 hours. Automatically:
  1. Loads today's predictions with edge data
  2. Builds the best accumulator (2-4 legs)
  3. If adjusted_edge >= 0.02 and avg_confidence >= 0.60:
       → Publishes the accumulator to the admin Telegram channel
  4. Stores the result as an AgentInsight

Rate limiting: only publishes once per 4-hour window to avoid spam.
Skips if no predictions with sufficient edge are available.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

MIN_EDGE = 0.02
MIN_CONFIDENCE = 0.60
MIN_LEGS = 2
MAX_LEGS = 4
PUBLISH_COOLDOWN_HOURS = 4


def _correlation_penalty(legs: List[dict]) -> float:
    """Penalise same-league combinations."""
    leagues = [leg.get("league", "") for leg in legs]
    seen: set = set()
    penalty = 0.0
    for lg in leagues:
        if lg in seen and lg:
            penalty += 0.015
        seen.add(lg)
    return penalty


def _build_accumulators(candidates: List[dict]) -> List[dict]:
    accs = []
    for n in range(MIN_LEGS, min(MAX_LEGS, len(candidates)) + 1):
        for combo in combinations(candidates, n):
            legs = list(combo)
            prob = 1.0
            odds = 1.0
            for leg in legs:
                pmap = {
                    "home": leg.get("home_prob", 0.33),
                    "draw": leg.get("draw_prob", 0.33),
                    "away": leg.get("away_prob", 0.33),
                }
                prob *= pmap.get(leg.get("best_side", "home"), 0.33)
                odds *= leg.get("best_odds", 1.5)

            if prob <= 0:
                continue

            fair = 1.0 / prob
            edge = prob - (1.0 / odds)
            penalty = _correlation_penalty(legs)
            adj_edge = edge - penalty
            avg_conf = sum(l.get("confidence", 0.5) for l in legs) / len(legs)
            b = odds - 1
            kelly = max(0, (b * prob - (1 - prob)) / b) if b > 0 else 0

            if adj_edge >= MIN_EDGE and avg_conf >= MIN_CONFIDENCE:
                accs.append({
                    "n_legs": n,
                    "legs": legs,
                    "combined_prob": round(prob, 4),
                    "combined_odds": round(odds, 2),
                    "fair_odds": round(fair, 2),
                    "combined_edge": round(edge, 4),
                    "correlation_penalty": round(penalty, 4),
                    "adjusted_edge": round(adj_edge, 4),
                    "avg_confidence": round(avg_conf, 3),
                    "kelly_stake": round(min(kelly, 0.03), 4),
                })

    accs.sort(key=lambda x: x["adjusted_edge"], reverse=True)
    return accs[:5]


def _format_accumulator_message(acc: dict, version: str = "4.7.5") -> str:
    legs = acc.get("legs", [])
    legs_text = ""
    for i, leg in enumerate(legs, 1):
        side_labels = {"home": "HOME WIN", "draw": "DRAW", "away": "AWAY WIN"}
        side = side_labels.get(leg.get("best_side", "home"), "HOME WIN")
        legs_text += (
            f"  {i}. {leg.get('home_team', '?')} vs {leg.get('away_team', '?')}\n"
            f"     → {side} @ {leg.get('best_odds', 0):.2f} "
            f"(conf: {leg.get('confidence', 0):.0%})\n"
        )

    adj = acc.get("adjusted_edge", 0)
    fire = "🔥🔥🔥" if adj > 0.05 else ("🔥🔥" if adj > 0.03 else "🔥")

    return (
        f"<b>🎰 VIT AUTO ACCUMULATOR</b>\n"
        f"{'━'*22}\n\n"
        f"<b>🏆 {acc['n_legs']}-Leg Accumulator</b>\n\n"
        f"<b>Selections:</b>\n{legs_text.strip()}\n\n"
        f"<b>📊 Combined Odds:</b> {acc['combined_odds']:.2f}\n"
        f"<b>📈 Edge:</b> {adj:+.2%} {fire}\n"
        f"<b>🎯 Avg Confidence:</b> {acc['avg_confidence']:.0%}\n"
        f"<b>💵 Suggested Stake:</b> {acc['kelly_stake']:.1%} of bankroll\n\n"
        f"{'━'*22}\n"
        f"<i>Auto-published by VIT Accumulator Agent v{version}</i>"
    )


class AccumulatorPublisherAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="accumulator-publisher",
            interval_seconds=2 * 60 * 60,
            initial_delay_seconds=240,
        )
        self._last_published_at: Optional[datetime] = None

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.db.models import Match, Prediction, AgentInsight
        from app.services.alerts import TelegramAlert, AlertPriority
        from sqlalchemy import select

        now = datetime.now(timezone.utc)

        # Rate limiting
        if self._last_published_at:
            elapsed = (now - self._last_published_at).total_seconds()
            if elapsed < PUBLISH_COOLDOWN_HOURS * 3600:
                remaining = int((PUBLISH_COOLDOWN_HOURS * 3600 - elapsed) / 60)
                return {"skipped": True, "reason": f"cooldown {remaining}min remaining"}

        # Load predictions with edge data for today's matches
        window_end = now + timedelta(hours=24)

        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(Match, Prediction)
                .join(Prediction, Prediction.match_id == Match.id)
                .where(
                    Match.kickoff_time >= now,
                    Match.kickoff_time <= window_end,
                    Match.status == "scheduled",
                    Prediction.home_prob.isnot(None),
                )
                .limit(30)
            )
            rows = res.all()

        candidates: List[dict] = []
        for match, pred in rows:
            if not pred or not pred.home_prob:
                continue

            # Determine best side
            probs = {
                "home": pred.home_prob or 0.33,
                "draw": pred.draw_prob or 0.33,
                "away": pred.away_prob or 0.33,
            }
            best_side = max(probs, key=lambda k: probs[k])
            best_prob = probs[best_side]

            # Estimate market odds (reciprocal with 5% margin)
            fair_odds = 1.0 / best_prob if best_prob > 0 else 3.0
            market_odds = fair_odds * 0.95  # approximate bookmaker price
            edge = best_prob - (1.0 / market_odds)

            conf_dict = getattr(pred, "confidence", {}) or {}
            if isinstance(conf_dict, dict):
                conf = conf_dict.get("1x2", 0.65)
            else:
                conf = float(conf_dict) if conf_dict else 0.65

            candidates.append({
                "match_id": match.id,
                "home_team": match.home_team,
                "away_team": match.away_team,
                "league": match.league or "",
                "home_prob": probs["home"],
                "draw_prob": probs["draw"],
                "away_prob": probs["away"],
                "best_side": best_side,
                "best_odds": round(market_odds, 2),
                "confidence": conf,
                "edge": round(edge, 4),
            })

        # Filter by minimum thresholds
        qualified = [c for c in candidates if c["confidence"] >= MIN_CONFIDENCE]

        if len(qualified) < MIN_LEGS:
            return {
                "skipped": True,
                "reason": f"only {len(qualified)} qualified candidates (need {MIN_LEGS})",
            }

        accumulators = _build_accumulators(qualified)

        if not accumulators:
            return {"skipped": True, "reason": "no accumulator met edge/confidence threshold"}

        best = accumulators[0]
        message = _format_accumulator_message(best)

        # Publish to Telegram
        published = False
        try:
            tg = TelegramAlert()
            published = await tg.send_message(message, AlertPriority.BET)
            if published:
                self._last_published_at = now
                logger.info(
                    "[accumulator-publisher] published %d-leg acc edge=%.3f",
                    best["n_legs"], best["adjusted_edge"],
                )
        except Exception as te:
            logger.warning("[accumulator-publisher] Telegram error: %s", te)

        # Store as AgentInsight
        async with AsyncSessionLocal() as db:
            insight = AgentInsight(
                agent_name="accumulator-publisher",
                insight_type="accumulator",
                ai_provider="ensemble",
                content=f"{best['n_legs']}-leg acc odds={best['combined_odds']:.2f} edge={best['adjusted_edge']:+.2%}",
                meta=best,
                confidence=best["avg_confidence"],
            )
            db.add(insight)
            await db.commit()

        return {
            "published": published,
            "n_legs": best["n_legs"],
            "combined_odds": best["combined_odds"],
            "adjusted_edge": best["adjusted_edge"],
            "avg_confidence": best["avg_confidence"],
            "candidates_evaluated": len(qualified),
        }
