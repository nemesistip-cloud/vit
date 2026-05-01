#!/usr/bin/env python3
"""Import 179 fixtures from attached_assets/all_fixtures_2may_18jun_1777678082560.csv

Matches are upserted by fingerprint to avoid duplicates on re-run.
Usage:  python scripts/import_fixtures.py
"""

import asyncio
import csv
import hashlib
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
import app.db.models  # noqa: F401 — trigger all relationship resolutions
import app.modules.wallet.models  # noqa: F401
import app.modules.blockchain.models  # noqa: F401
import app.modules.training.models  # noqa: F401
import app.modules.ai.models  # noqa: F401
import app.data.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401
import app.modules.marketplace.models  # noqa: F401
import app.modules.trust.models  # noqa: F401
import app.modules.rewards.models  # noqa: F401
import app.modules.bridge.models  # noqa: F401
import app.modules.developer.models  # noqa: F401
import app.modules.governance.models  # noqa: F401
import app.modules.referral.models  # noqa: F401
import app.modules.tasks.models  # noqa: F401
from app.db.models import Match

# ── Timezone offset map for kickoff conversion (all times in the CSV are
#    local-event times which we treat as UTC for simplicity) ──────────────────
_CSV_PATH = Path(__file__).parents[1] / "attached_assets" / "all_fixtures_2may_18jun_1777678082560.csv"

_MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _parse_kickoff(date_str: str, time_str: str, year: int = 2026) -> datetime:
    """Parse '2 May' + '12:30' into an aware UTC datetime."""
    parts = date_str.strip().split()
    day = int(parts[0])
    month = _MONTH_MAP[parts[1]]
    hour, minute = map(int, time_str.strip().split(":"))
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _make_fingerprint(kickoff: datetime, home: str, away: str, league: str) -> str:
    raw = f"{kickoff.date()}::{home.lower().strip()}::{away.lower().strip()}::{league.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


async def import_fixtures():
    if not _CSV_PATH.exists():
        print(f"[error] CSV not found at {_CSV_PATH}")
        sys.exit(1)

    rows = []
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip comment rows / header variants
            if row.get("#", "").startswith("#") or not row.get("home"):
                continue
            rows.append(row)

    print(f"[import] Loaded {len(rows)} rows from CSV")

    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        for row in rows:
            try:
                kickoff = _parse_kickoff(row["date"], row["time"])
            except Exception as e:
                print(f"[warn] Skipping row (date parse error): {row} — {e}")
                skipped += 1
                continue

            home = row["home"].strip()
            away = row["away"].strip()
            league = row["league"].strip()
            fp = _make_fingerprint(kickoff, home, away, league)

            existing = await db.execute(
                select(Match).where(Match.fingerprint == fp)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            try:
                home_odds = float(row["H"]) if row.get("H") else None
                draw_odds = float(row["D"]) if row.get("D") else None
                away_odds = float(row["A"]) if row.get("A") else None
            except ValueError:
                home_odds = draw_odds = away_odds = None

            match = Match(
                home_team=home,
                away_team=away,
                league=league,
                kickoff_time=kickoff,
                status="scheduled",
                source="user_csv",
                fingerprint=fp,
                opening_odds_home=home_odds,
                opening_odds_draw=draw_odds,
                opening_odds_away=away_odds,
            )
            db.add(match)
            inserted += 1

        if inserted:
            await db.commit()

    print(f"[import] Done — {inserted} inserted, {skipped} skipped (already exist or parse error)")


if __name__ == "__main__":
    asyncio.run(import_fixtures())
