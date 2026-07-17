import asyncio
import hashlib
import random
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import Match

# --- HIGH PROFILE DATA ---
WORLD_CUP_FIXTURES = [
    {"time": "2026-06-28 17:00:00", "league": "International - FIFA World Cup", "home_team": "Spain", "away_team": "Portugal", "odds_home": 2.10, "odds_draw": 3.40, "odds_away": 3.60},
    {"time": "2026-06-28 21:00:00", "league": "International - FIFA World Cup", "home_team": "Netherlands", "away_team": "France", "odds_home": 3.20, "odds_draw": 3.30, "odds_away": 2.25},
    {"time": "2026-06-28 14:00:00", "league": "International - FIFA World Cup", "home_team": "Brazil", "away_team": "Germany", "odds_home": 1.95, "odds_draw": 3.50, "odds_away": 3.80},
    {"time": "2026-06-28 11:00:00", "league": "International - FIFA World Cup", "home_team": "Argentina", "away_team": "England", "odds_home": 2.40, "odds_draw": 3.20, "odds_away": 3.10},
    {"time": "2026-06-29 17:00:00", "league": "International - FIFA World Cup", "home_team": "Italy", "away_team": "Belgium", "odds_home": 2.60, "odds_draw": 3.10, "odds_away": 2.80},
    {"time": "2026-06-29 21:00:00", "league": "International - FIFA World Cup", "home_team": "Uruguay", "away_team": "Croatia", "odds_home": 2.30, "odds_draw": 3.20, "odds_away": 3.25},
    {"time": "2026-06-29 14:00:00", "league": "International - FIFA World Cup", "home_team": "Senegal", "away_team": "USA", "odds_home": 2.70, "odds_draw": 3.00, "odds_away": 2.85},
    {"time": "2026-06-30 18:00:00", "league": "International - FIFA World Cup", "home_team": "Morocco", "away_team": "Japan", "odds_home": 2.20, "odds_draw": 3.10, "odds_away": 3.50},
    {"time": "2026-06-30 21:00:00", "league": "International - FIFA World Cup", "home_team": "Mexico", "away_team": "Switzerland", "odds_home": 2.50, "odds_draw": 3.20, "odds_away": 3.00},
]

TENNIS_FIXTURES = [
    {"time": "2026-06-28 13:00:00", "league": "Tennis - ATP Wimbledon", "home_team": "Jannik Sinner", "away_team": "Carlos Alcaraz", "odds_home": 1.85, "odds_draw": None, "odds_away": 1.95},
    {"time": "2026-06-28 15:30:00", "league": "Tennis - ATP Wimbledon", "home_team": "Novak Djokovic", "away_team": "Lorenzo Musetti", "odds_home": 1.15, "odds_draw": None, "odds_away": 5.50},
    {"time": "2026-06-28 16:00:00", "league": "Tennis - ATP Wimbledon", "home_team": "Daniil Medvedev", "away_team": "Alexander Zverev", "odds_home": 2.10, "odds_draw": None, "odds_away": 1.75},
    {"time": "2026-06-28 14:00:00", "league": "Tennis - WTA Wimbledon", "home_team": "Iga Swiatek", "away_team": "Aryna Sabalenka", "odds_home": 1.65, "odds_draw": None, "odds_away": 2.25},
]

LEAGUES = [
    "England - Premier League", "Spain - LaLiga", "Italy - Serie A",
    "Germany - Bundesliga", "France - Ligue 1", "USA - MLS",
    "Brazil - Serie A", "Japan - J1 League", "Netherlands - Eredivisie",
    "Portugal - Liga Portugal", "Saudi - Pro League", "Mexico - Liga MX",
    "Argentina - Primera Division", "Turkey - Super Lig"
]

TEAM_BASES = ["Phoenix", "Dragons", "Lions", "Wolves", "Giants", "Hawks", "Titans", "Foxes", "Rangers", "Knights", "Sparks", "Oaks", "Stalkers", "Flares", "Eagles"]

def _make_fingerprint(kickoff: datetime, home: str, away: str, league: str) -> str:
    raw = f"{kickoff.date()}::{home.lower().strip()}::{away.lower().strip()}::{league.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()

async def seed():
    random.seed(42)
    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        # 1. High Profile
        for f in WORLD_CUP_FIXTURES + TENNIS_FIXTURES:
            kickoff = datetime.fromisoformat(f["time"]).replace(tzinfo=timezone.utc)
            fp = _make_fingerprint(kickoff, f["home_team"], f["away_team"], f["league"])
            existing = await db.execute(select(Match).where(Match.fingerprint == fp))
            if existing.scalar_one_or_none():
                skipped += 1
                continue
            db.add(Match(
                home_team=f["home_team"], away_team=f["away_team"], league=f["league"],
                kickoff_time=kickoff, status="scheduled", source="seed_high_profile",
                fingerprint=fp, market_type="sports", sport="tennis" if "tennis" in f["league"].lower() else "football",
                opening_odds_home=f.get("odds_home"), opening_odds_draw=f.get("odds_draw"), opening_odds_away=f.get("odds_away")
            ))
            inserted += 1

        # 2. Mass fixtures (1500 matches)
        start_dt = datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc)
        for i in range(1500):
            day_offset = i // 40
            current_date = start_dt + timedelta(days=day_offset)
            league = random.choice(LEAGUES)
            h_name = f"{random.choice(TEAM_BASES)} FC ({i})"
            a_name = f"{random.choice(TEAM_BASES)} Utd ({i})"
            kickoff = current_date.replace(hour=random.randint(10, 22), minute=random.choice([0, 30]))
            fp = _make_fingerprint(kickoff, h_name, a_name, league)

            db.add(Match(
                home_team=h_name, away_team=a_name, league=league,
                kickoff_time=kickoff, status="scheduled", source="seed_mass",
                fingerprint=fp, market_type="sports",
                opening_odds_home=round(random.uniform(1.5, 3.5), 2),
                opening_odds_draw=round(random.uniform(3.0, 4.5), 2),
                opening_odds_away=round(random.uniform(1.5, 4.5), 2)
            ))
            inserted += 1
            if inserted % 300 == 0:
                print(f"Batch committed... {inserted} total matches.")
                await db.commit()

        await db.commit()
    print(f"Seeding finished. Inserted: {inserted}, Skipped: {skipped}")

if __name__ == "__main__":
    asyncio.run(seed())
