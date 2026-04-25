"""
CLV streak monitor — closes the loop on the model accountability system.

Runs daily-ish from inside the existing `model_accountability_loop`. For each
active model:
  - If its rolling `clv_score` is below the demote threshold AND it has
    enough samples to trust the signal, increment the negative-streak
    counter (once per day, not per loop tick).
  - Otherwise, reset the streak.
  - If the streak hits CLV_DEMOTE_DAYS, flip `is_active=False` and
    `auto_demoted=True`. The predictor and weight adjuster already filter on
    `is_active=True`, so the model stops contributing immediately.

Manual reactivation (the admin "Reactivate" button on the dashboard) clears
both the streak and the auto_demoted flag so the timer doesn't fire again on
the next tick.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import ModelMetadata

logger = logging.getLogger(__name__)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


CLV_DEMOTE_THRESHOLD: float = _env_float("CLV_DEMOTE_THRESHOLD", -0.005)
CLV_DEMOTE_DAYS:      int   = _env_int("CLV_DEMOTE_DAYS", 7)
CLV_MIN_SAMPLES:      int   = _env_int("CLV_DEMOTE_MIN_SAMPLES", 50)
# Daily cadence with a little slack so a loop that fires every 6h still ticks
# the counter exactly once per calendar day rather than four times.
CLV_CHECK_MIN_HOURS:  float = _env_float("CLV_CHECK_MIN_HOURS", 18.0)


async def check_clv_streaks(db: AsyncSession) -> Dict:
    """
    Walk every active model row, advance or reset its negative-CLV streak,
    and demote rows that have crossed the threshold for too long.

    Returns a summary dict for logging:
        {
          "checked": int,            # rows considered
          "ticked": int,             # rows that actually advanced today
          "skipped_recent": int,     # rows skipped because last_clv_check_at was too recent
          "skipped_low_samples": int,
          "demoted": [keys...],      # rows the monitor just turned off
          "incremented": [(key, new_streak), ...],
          "reset": [keys...],
        }
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=CLV_CHECK_MIN_HOURS)

    rows = (await db.execute(
        select(ModelMetadata).where(ModelMetadata.is_active.is_(True))
    )).scalars().all()

    summary = {
        "checked": len(rows),
        "ticked": 0,
        "skipped_recent": 0,
        "skipped_low_samples": 0,
        "demoted": [],
        "incremented": [],
        "reset": [],
    }

    for row in rows:
        # Once-per-day guard so faster loop cadences don't inflate the streak.
        if row.last_clv_check_at and row.last_clv_check_at > cutoff:
            summary["skipped_recent"] += 1
            continue

        samples = int(row.clv_samples or 0)
        if samples < CLV_MIN_SAMPLES:
            # Not enough data to judge — don't tick the streak in either
            # direction, but still record that we looked so the cadence guard
            # works once samples accumulate.
            row.last_clv_check_at = now
            summary["skipped_low_samples"] += 1
            continue

        clv = float(row.clv_score) if row.clv_score is not None else 0.0
        row.last_clv_check_at = now
        summary["ticked"] += 1

        if clv < CLV_DEMOTE_THRESHOLD:
            row.clv_negative_streak_days = int(row.clv_negative_streak_days or 0) + 1
            summary["incremented"].append((row.key, row.clv_negative_streak_days))

            if row.clv_negative_streak_days >= CLV_DEMOTE_DAYS:
                row.is_active = False
                row.auto_demoted = True
                summary["demoted"].append(row.key)
                logger.warning(
                    "[clv-monitor] AUTO-DEMOTED %s — clv_score=%.4f for %d consecutive days "
                    "(threshold=%.4f, min_samples=%d). Reactivate from Admin → Models → "
                    "Accountability when investigated.",
                    row.key, clv, row.clv_negative_streak_days,
                    CLV_DEMOTE_THRESHOLD, CLV_MIN_SAMPLES,
                )
        else:
            if (row.clv_negative_streak_days or 0) > 0:
                summary["reset"].append(row.key)
            row.clv_negative_streak_days = 0

    await db.commit()
    return summary
