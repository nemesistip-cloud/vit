"""app/services/prediction_seeder.py — Phase 3a-2
Seeds synthetic predictions for historical settled matches so that ML
performance tracking, CLV backfill, and bankroll stats have real data.

Generates 2–4 Prediction rows per settled Match that doesn't already
have predictions. Each prediction has realistic probabilities, odds,
and correct settlement (was_correct, settled_profit).
"""
from __future__ import annotations

import logging
import random
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match, Prediction

logger = logging.getLogger(__name__)

random.seed(42)  # Reproducible seeds across restarts

_ALERT_CONFIDENCE_THRESHOLD = 0.68  # Only notify for picks with ≥68 % confidence

MODEL_SOURCES = [
    "xgb_v1", "lgb_v1", "nn_v1", "poisson_v1",
    "xgb_v2", "lgb_v2", "nn_v2", "ensemble_v1",
]

LEAGUE_PRIORS = {
    "premier_league":           (0.36, 0.28, 0.36),
    "la_liga":                  (0.36, 0.28, 0.36),
    "bundesliga":               (0.36, 0.28, 0.36),
    "serie_a":                  (0.36, 0.28, 0.36),
    "ligue_1":                  (0.36, 0.28, 0.36),
    "champions_league":         (0.36, 0.28, 0.36),
    "europa_league":            (0.36, 0.28, 0.36),
    "conference_league":        (0.36, 0.28, 0.36),
    "eredivisie":               (0.36, 0.28, 0.36),
    "primeira_liga":            (0.36, 0.28, 0.36),
    "championship":             (0.36, 0.28, 0.36),
    "scottish_premiership":     (0.36, 0.28, 0.36),
    "belgian_pro_league":       (0.36, 0.28, 0.36),
    "super_lig":                (0.36, 0.28, 0.36),
    "ekstraklasa":              (0.36, 0.28, 0.36),
    "mls":                      (0.36, 0.28, 0.36),
    "liga_mx":                  (0.36, 0.28, 0.36),
    "brasileirao":              (0.36, 0.28, 0.36),
    "brazil_serie_a":           (0.36, 0.28, 0.36),
    "argentine_primera":        (0.36, 0.28, 0.36),
    "argentina_liga_profesional": (0.36, 0.28, 0.36),
}


def _normalize(h: float, d: float, a: float):
    total = h + d + a
    return h / total, d / total, a / total


def _fair_odds(prob: float) -> float:
    if prob <= 0:
        return 99.0
    return round(1.0 / prob * random.uniform(0.92, 0.97), 2)  # apply vig


def _seed_hash(match_id: int, seed_idx: int) -> str:
    return hashlib.sha256(f"seed:{match_id}:{seed_idx}".encode()).hexdigest()[:32]


def _balance_home_advantage(h: float, d: float, a: float) -> tuple[float, float, float]:
    """Ensure synthetic predictions are balanced and unbiased between home and away outcomes."""
    spread = h - a
    if abs(spread) > 0.02:
        mid = (h + a) / 2.0
        h = mid + (h - mid) * 0.5
        a = mid + (a - mid) * 0.5
    h, d, a = _normalize(max(0.05, h), max(0.05, d), max(0.05, a))
    return h, d, a


def _make_prediction(match: Match, seed_idx: int, win_bias: float = 0.60) -> Optional[Prediction]:
    prior = LEAGUE_PRIORS.get(match.league or "", (0.37, 0.27, 0.36))
    h_base, d_base, a_base = prior

    # Counteract the synthetic home-bias that can otherwise dominate all picks.
    if h_base > a_base + 0.08:
        h_base -= (h_base - a_base) * 0.55
        a_base += (h_base - a_base) * 0.55

    noise = 0.08
    h = h_base + random.uniform(-noise, noise)
    d = d_base + random.uniform(-noise * 0.5, noise * 0.5)
    a = a_base + random.uniform(-noise, noise)
    h, d, a = _balance_home_advantage(h, d, a)

    bet_side = max([("home", h), ("draw", d), ("away", a)], key=lambda x: x[1])[0]

    actual = match.actual_outcome or "home"
    was_correct = bet_side == actual

    entry_odds = _fair_odds({"home": h, "draw": d, "away": a}[bet_side])
    recommended_stake = round(random.uniform(0.01, 0.04), 4)

    if was_correct:
        settled_profit = round((entry_odds - 1) * recommended_stake, 4)
    else:
        settled_profit = round(-recommended_stake, 4)

    kickoff = match.kickoff_time
    if kickoff:
        naive_base = kickoff if kickoff.tzinfo is None else kickoff.replace(tzinfo=None)
        pred_time = (naive_base - timedelta(hours=random.uniform(1, 48))).replace(tzinfo=timezone.utc)
    else:
        pred_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))

    req_hash = _seed_hash(match.id, seed_idx)

    return Prediction(
        match_id=match.id,
        status="READY",
        source="seed_demo",
        is_seed=True,
        provenance={"source": "prediction_seeder", "seed_idx": seed_idx},
        user_id=None,
        request_hash=req_hash,
        home_prob=round(h, 4),
        draw_prob=round(d, 4),
        away_prob=round(a, 4),
        over_25_prob=round(random.uniform(0.45, 0.75), 4),
        under_25_prob=None,
        btts_prob=round(random.uniform(0.40, 0.65), 4),
        consensus_prob=round(max(h, d, a), 4),
        final_ev=round(({"home": h, "draw": d, "away": a}[bet_side] * entry_odds - 1), 4),
        recommended_stake=recommended_stake,
        confidence=round(max(h, d, a), 4),
        bet_side=bet_side,
        entry_odds=entry_odds,
        raw_edge=round({"home": h, "draw": d, "away": a}[bet_side] - 1 / entry_odds, 4),
        normalized_edge=round({"home": h, "draw": d, "away": a}[bet_side] - 1 / entry_odds * 0.95, 4),
        vig_free_edge=None,
        was_correct=was_correct,
        settled_profit=settled_profit,
        timestamp=pred_time,
    )


async def seed_predictions_for_historical(
    db: AsyncSession,
    preds_per_match: int = 3,
    max_matches: int = 300,
) -> Dict:
    """
    For every settled Match (with actual_outcome) that has no predictions yet,
    generate `preds_per_match` synthetic Prediction rows.
    """
    settled_res = await db.execute(
        select(Match).where(
            Match.actual_outcome.isnot(None)
        ).order_by(Match.kickoff_time.desc()).limit(max_matches)
    )
    settled_matches = settled_res.scalars().all()

    if not settled_matches:
        return {"seeded": 0, "skipped": 0, "matches_checked": 0}

    seeded = 0
    skipped = 0

    for match in settled_matches:
        existing_res = await db.execute(
            select(func.count(Prediction.id)).where(Prediction.match_id == match.id)
        )
        existing_count = existing_res.scalar_one_or_none() or 0

        if existing_count >= preds_per_match:
            skipped += 1
            continue

        needed = preds_per_match - existing_count
        for i in range(needed):
            pred = _make_prediction(match, seed_idx=existing_count + i)
            if pred:
                db.add(pred)
                seeded += 1

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("[prediction-seeder] commit error: %s", e)
        return {"seeded": 0, "skipped": skipped, "matches_checked": len(settled_matches), "error": str(e)}

    logger.info(
        "[prediction-seeder] seeded=%d skipped=%d matches_checked=%d",
        seeded, skipped, len(settled_matches),
    )
    return {"seeded": seeded, "skipped": skipped, "matches_checked": len(settled_matches)}


async def seed_upcoming_predictions(
    db: AsyncSession,
    preds_per_match: int = 3,
    max_matches: int = 500,
) -> Dict:
    """
    Refuse to fabricate predictions for upcoming matches.

    Upcoming predictions must be generated by the live orchestrator after
    provider evidence has been collected. Historical seeding remains available
    for analytics, but synthetic rows must never appear as current picks.
    """
    logger.warning("[upcoming-seeder] disabled: live provider evidence is required")
    return {
        "seeded": 0,
        "skipped": 0,
        "matches_checked": 0,
        "alerts_sent": 0,
        "disabled": True,
        "reason": "Upcoming predictions require live provider evidence",
    }
