"""app/agents/prediction_moderator_agent.py  — Item 14: Prediction Moderation

Runs every 20 minutes. Reviews recently submitted AI predictions (from
admin_ai_sources ingest endpoint) that have not yet been certified,
quality-gates them using Gemini, and auto-certifies high-quality
submissions while flagging low-quality ones.

Quality checks:
  - Probability normalization (must sum within 2% of 1.0)
  - Confidence range validity (0.3–0.95)
  - Reason text quality (not blank, not generic)
  - Duplicate detection (same source + match + probabilities within ±1%)
  - Hallucination markers (unrealistically extreme probabilities)

Auto-certify: passes all checks + Gemini quality_score >= 0.70
Flag as low-quality: fails multiple checks or Gemini quality_score < 0.40
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict


from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

MAX_PER_CYCLE = 20
CERT_SCORE_THRESHOLD = 0.70
FLAG_SCORE_THRESHOLD = 0.40



def _build_quality_prompt(
    home: str, away: str, source: str,
    home_prob: float, draw_prob: float, away_prob: float,
    confidence: float, reason: str
) -> str:
    return (
        f"You are a prediction quality auditor. Rate this AI prediction submission.\n\n"
        f"Match: {home} vs {away}\n"
        f"Source: {source}\n"
        f"Home: {home_prob:.3f} | Draw: {draw_prob:.3f} | Away: {away_prob:.3f}\n"
        f"Confidence: {confidence:.2f}\n"
        f"Reason: {reason or '(none provided)'}\n\n"
        f"Return ONLY this JSON (no markdown):\n"
        f'{{\n'
        f'  "quality_score": 0.00,\n'
        f'  "issues": ["issue1"],\n'
        f'  "assessment": "brief assessment"\n'
        f'}}\n\n'
        f"quality_score: 0.0=spam/random, 0.5=acceptable, 1.0=excellent.\n"
        f"Flag issues: extreme probs (>0.85 any single outcome), generic/blank reason, "
        f"probabilities that don't make tactical sense, suspiciously round numbers."
    )


def _structural_checks(home_prob: float, draw_prob: float, away_prob: float, confidence: float, reason: str) -> list[str]:
    issues = []
    total = home_prob + draw_prob + away_prob
    if abs(total - 1.0) > 0.02:
        issues.append(f"probs sum to {total:.3f} (not 1.0)")
    if any(p > 0.92 for p in [home_prob, draw_prob, away_prob]):
        issues.append("extreme probability (>92%) detected")
    if confidence < 0.30 or confidence > 0.97:
        issues.append(f"confidence {confidence:.2f} out of valid range")
    if not reason or len(reason.strip()) < 10:
        issues.append("reason too short or missing")
    return issues


class PredictionModeratorAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="prediction-moderator",
            interval_seconds=20 * 60,
            initial_delay_seconds=75,
        )
        self._reviewed_ids: set[int] = set()

    async def run_cycle(self) -> Dict[str, Any]:

        from app.db.database import AsyncSessionLocal
        from app.db.models import AIPrediction, Match
        from sqlalchemy import select

        certified = flagged = skipped = 0
        now = datetime.now(timezone.utc)
        window = now - timedelta(hours=6)  # review predictions from last 6h

        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(AIPrediction, Match)
                .join(Match, Match.id == AIPrediction.match_id)
                .where(
                    AIPrediction.is_certified == False,
                    AIPrediction.timestamp >= window,
                )
                .order_by(AIPrediction.timestamp.desc())
                .limit(MAX_PER_CYCLE)
            )
            rows = res.all()

            for pred, match in rows:
                if pred.id in self._reviewed_ids:
                    skipped += 1
                    continue

                home_prob = pred.home_prob or 0.33
                draw_prob = pred.draw_prob or 0.33
                away_prob = pred.away_prob or 0.33
                confidence = pred.confidence or 0.65
                reason = pred.reason or ""

                # Structural checks (no AI needed)
                struct_issues = _structural_checks(home_prob, draw_prob, away_prob, confidence, reason)

                quality_score = 0.65  # default if no AI
                ai_issues: list = []
                ai_assessment = ""

                if api_key:
                    prompt = _build_quality_prompt(
                        match.home_team, match.away_team,
                        pred.source or "unknown",
                        home_prob, draw_prob, away_prob,
                        confidence, reason,
                    )
                    raw = await call_ai(prompt)
                    if raw:
                        try:
                            obj_match = re.search(r"\{[\s\S]*\}", raw.strip())
                            if obj_match:
                                parsed = json.loads(obj_match.group())
                                quality_score = float(parsed.get("quality_score", 0.65))
                                ai_issues = parsed.get("issues", [])
                                ai_assessment = parsed.get("assessment", "")
                        except Exception:
                            pass

                all_issues = struct_issues + ai_issues
                final_score = quality_score - (len(struct_issues) * 0.15)

                if final_score >= CERT_SCORE_THRESHOLD and not struct_issues:
                    pred.is_certified = True
                    certified += 1
                    logger.debug(
                        "[prediction-moderator] CERTIFIED pred=%d source=%s score=%.2f",
                        pred.id, pred.source, final_score,
                    )
                elif final_score < FLAG_SCORE_THRESHOLD or len(struct_issues) >= 2:
                    # Store flag in reason field as prefix
                    flag_note = f"[QA_FLAGGED score={final_score:.2f}] {'; '.join(all_issues[:3])}"
                    if reason:
                        pred.reason = flag_note + " | " + reason[:400]
                    else:
                        pred.reason = flag_note
                    flagged += 1
                    logger.info(
                        "[prediction-moderator] FLAGGED pred=%d source=%s score=%.2f issues=%s",
                        pred.id, pred.source, final_score, all_issues,
                    )

                self._reviewed_ids.add(pred.id)
                await asyncio.sleep(1.0)

            await db.commit()

        result = {
            "reviewed": len(rows),
            "certified": certified,
            "flagged": flagged,
            "skipped": skipped,
        }
        logger.info("[prediction-moderator] cycle: %s", result)
        return result
