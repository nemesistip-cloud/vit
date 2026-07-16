"""
Closing Line Value backfill (v4.6.1).

Scans settled Predictions that have no CLVEntry row (or whose row never got
its closing odds filled in) and rebuilds the entry from the closing odds we
already have stored on the Match.

Two entry points:
- `backfill_missing_clv(db)`              — used by background loop + admin endpoint
- a thin admin route in `app/api/routes/admin_clv.py` re-exports it as HTTP
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CLVEntry, Match, Prediction
from app.services.clv_tracker import CLVTracker

logger = logging.getLogger(__name__)


def _profit_from_outcome(
    bet_side: str, actual_outcome: str, stake: float, odds: float,
) -> tuple[float, str]:
    """Return (profit, win/loss/void)."""
    if not bet_side or actual_outcome is None:
        return 0.0, "void"
    won = bet_side == actual_outcome
    return (stake * (odds - 1) if won else -stake), ("win" if won else "loss")


def _side_closing_odds(match: Match, bet_side: str) -> Optional[float]:
    return {
        "home": match.closing_odds_home,
        "draw": match.closing_odds_draw,
        "away": match.closing_odds_away,
    }.get(bet_side)


async def backfill_missing_clv(
    db: AsyncSession, *, limit: int = 500, dry_run: bool = False,
) -> Dict[str, int]:
    """
    Rebuild CLV rows for settled predictions that are missing them.

    Iterates settled predictions (Match.actual_outcome is set) where the
    paired CLVEntry is either absent or has no `clv` populated yet, then
    fills it from the Match's stored closing odds.

    Returns a counter dict with `scanned`, `created`, `updated`, `skipped`,
    `missing_closing_odds`.
    """
    counts = {
        "scanned": 0, "created": 0, "updated": 0,
        "skipped": 0, "missing_closing_odds": 0,
    }

    # Pull settled predictions with a real bet_side and entry_odds.
    pred_rows = await db.execute(
        select(Prediction, Match)
        .join(Match, Prediction.match_id == Match.id)
        .where(Match.actual_outcome.isnot(None))
        .where(Prediction.bet_side.isnot(None))
        .where(Prediction.entry_odds.isnot(None))
        .order_by(Prediction.timestamp.desc())
        .limit(limit)
    )

    todo: List[tuple[Prediction, Match, Optional[CLVEntry]]] = []
    for pred, match in pred_rows.all():
        counts["scanned"] += 1
        existing_q = await db.execute(
            select(CLVEntry).where(CLVEntry.prediction_id == pred.id)
        )
        existing = existing_q.scalar_one_or_none()
        # Skip rows that are already fully populated.
        if existing and existing.clv is not None and existing.closing_odds is not None:
            counts["skipped"] += 1
            continue
        todo.append((pred, match, existing))

    for pred, match, existing in todo:
        closing = _side_closing_odds(match, pred.bet_side)
        if closing is None or closing <= 0:
            counts["missing_closing_odds"] += 1
            continue

        stake  = float(pred.recommended_stake or 0.0)
        odds   = float(pred.entry_odds or 0.0)
        profit, outcome_label = _profit_from_outcome(
            pred.bet_side, match.actual_outcome, stake, odds,
        )
        clv = CLVTracker.calculate_clv(odds, float(closing))

        if dry_run:
            continue

        if existing is None:
            db.add(CLVEntry(
                match_id      = match.id,
                prediction_id = pred.id,
                bet_side      = pred.bet_side,
                entry_odds    = odds,
                closing_odds  = float(closing),
                clv           = clv,
                bet_outcome   = outcome_label,
                profit        = profit,
            ))
            counts["created"] += 1
        else:
            existing.closing_odds = float(closing)
            existing.clv          = clv
            existing.bet_outcome  = outcome_label
            existing.profit       = profit
            counts["updated"] += 1

    if not dry_run and (counts["created"] or counts["updated"]):
        await db.commit()
        logger.info(
            "[clv-backfill] created=%d updated=%d scanned=%d skipped=%d missing=%d",
            counts["created"], counts["updated"], counts["scanned"],
            counts["skipped"], counts["missing_closing_odds"],
        )
    return counts
