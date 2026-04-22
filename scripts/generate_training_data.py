#!/usr/bin/env python3
"""
VIT Sports Intelligence Network — Training Data Generator
==========================================================
Generates synthetic but realistic historical football match data for
model training when real match data is unavailable or insufficient.

The synthetic data is based on empirical distributions from real-world
football match outcomes and bookmaker odds patterns.

Usage:
  python scripts/generate_training_data.py                       # 5000 samples
  python scripts/generate_training_data.py --samples 10000       # custom count
  python scripts/generate_training_data.py --output data/custom.csv
  python scripts/generate_training_data.py --with-db             # also pull DB rows
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_OUTPUT = ROOT / "data" / "training" / "matches.csv"
DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# Realistic league-specific parameters based on historical data
LEAGUE_CONFIGS = {
    "Premier League": {"home_win_rate": 0.44, "draw_rate": 0.24, "avg_goals": 2.67},
    "La Liga":        {"home_win_rate": 0.46, "draw_rate": 0.23, "avg_goals": 2.73},
    "Bundesliga":     {"home_win_rate": 0.43, "draw_rate": 0.22, "avg_goals": 3.05},
    "Serie A":        {"home_win_rate": 0.43, "draw_rate": 0.26, "avg_goals": 2.50},
    "Ligue 1":        {"home_win_rate": 0.45, "draw_rate": 0.26, "avg_goals": 2.55},
    "Champions League":{"home_win_rate": 0.40, "draw_rate": 0.22, "avg_goals": 2.85},
    "Europa League":  {"home_win_rate": 0.38, "draw_rate": 0.25, "avg_goals": 2.60},
}

LEAGUES = list(LEAGUE_CONFIGS.keys())


def implied_prob(odds: float) -> float:
    return 1.0 / max(odds, 1.01)


def generate_match_row(rng: np.random.Generator, league_config: dict) -> dict:
    """Generate a single realistic match row with full feature set."""
    hw_rate = league_config["home_win_rate"]
    dr_rate = league_config["draw_rate"]
    aw_rate = 1.0 - hw_rate - dr_rate
    avg_goals = league_config["avg_goals"]

    # Draw true outcome from league distribution
    outcome_val = rng.random()
    if outcome_val < hw_rate:
        outcome = "home"
        label = "H"
    elif outcome_val < hw_rate + dr_rate:
        outcome = "draw"
        label = "D"
    else:
        outcome = "away"
        label = "A"

    # Simulate bookmaker odds with realistic vig (2-5%)
    vig = rng.uniform(1.02, 1.05)
    noise_h = rng.uniform(0.88, 1.12)
    noise_d = rng.uniform(0.92, 1.08)
    noise_a = rng.uniform(0.88, 1.12)

    raw_h = hw_rate * noise_h
    raw_d = dr_rate * noise_d
    raw_a = aw_rate * noise_a
    total = raw_h + raw_d + raw_a

    # Odds = vig / fair_prob
    home_odds = round(vig / max(raw_h / total, 0.05), 2)
    draw_odds = round(vig / max(raw_d / total, 0.05), 2)
    away_odds = round(vig / max(raw_a / total, 0.05), 2)

    # Implied probabilities (overround removed)
    inv = implied_prob(home_odds) + implied_prob(draw_odds) + implied_prob(away_odds)
    home_implied = implied_prob(home_odds) / inv
    draw_implied = implied_prob(draw_odds) / inv
    away_implied = implied_prob(away_odds) / inv

    # Team form features (0=poor, 1=excellent)
    home_str = rng.beta(5, 5) * 0.6 + home_implied * 0.4
    away_str = rng.beta(5, 5) * 0.6 + away_implied * 0.4

    home_form_w3 = float(np.clip(home_str + rng.normal(0, 0.08), 0.1, 0.9))
    home_form_w5 = float(np.clip(home_str + rng.normal(0, 0.06), 0.1, 0.9))
    home_form_w10 = float(np.clip(home_str + rng.normal(0, 0.04), 0.1, 0.9))
    away_form_w3 = float(np.clip(away_str + rng.normal(0, 0.08), 0.1, 0.9))
    away_form_w5 = float(np.clip(away_str + rng.normal(0, 0.06), 0.1, 0.9))
    away_form_w10 = float(np.clip(away_str + rng.normal(0, 0.04), 0.1, 0.9))

    # Goals features
    home_goals_avg = float(np.clip(avg_goals * 0.55 * (0.5 + home_str) + rng.normal(0, 0.2), 0.3, 3.5))
    away_goals_avg = float(np.clip(avg_goals * 0.45 * (0.5 + away_str) + rng.normal(0, 0.2), 0.3, 3.0))
    home_goals_conceded_avg = float(np.clip(avg_goals * 0.45 * (1.5 - home_str) + rng.normal(0, 0.15), 0.3, 2.8))
    away_goals_conceded_avg = float(np.clip(avg_goals * 0.55 * (1.5 - away_str) + rng.normal(0, 0.15), 0.3, 3.2))

    # xG (correlated with goals but with variance)
    home_xg_avg = float(np.clip(home_goals_avg * rng.uniform(0.85, 1.15), 0.2, 3.0))
    away_xg_avg = float(np.clip(away_goals_avg * rng.uniform(0.85, 1.15), 0.2, 2.5))

    # Head-to-head record (0-10 games)
    h2h_total = int(rng.integers(0, 11))
    if h2h_total > 0:
        h2h_probs = np.array([hw_rate, dr_rate, aw_rate])
        h2h_split = rng.multinomial(h2h_total, h2h_probs / h2h_probs.sum())
        h2h_home_wins, h2h_draws, h2h_away_wins = int(h2h_split[0]), int(h2h_split[1]), int(h2h_split[2])
    else:
        h2h_home_wins = h2h_draws = h2h_away_wins = 0

    # Rest days since last match
    days_home = int(rng.choice([3, 4, 7, 7, 7, 10, 14], p=[0.05, 0.10, 0.45, 0.15, 0.10, 0.10, 0.05]))
    days_away = int(rng.choice([3, 4, 7, 7, 7, 10, 14], p=[0.05, 0.10, 0.45, 0.15, 0.10, 0.10, 0.05]))

    return {
        "outcome": outcome,
        "result": label,
        "home_odds": home_odds,
        "draw_odds": draw_odds,
        "away_odds": away_odds,
        "home_implied_prob": round(home_implied, 4),
        "draw_implied_prob": round(draw_implied, 4),
        "away_implied_prob": round(away_implied, 4),
        "vig": round(inv - 1.0, 4),
        "home_advantage": 1.0,
        "home_form_w3": round(home_form_w3, 4),
        "home_form_w5": round(home_form_w5, 4),
        "home_form_w10": round(home_form_w10, 4),
        "away_form_w3": round(away_form_w3, 4),
        "away_form_w5": round(away_form_w5, 4),
        "away_form_w10": round(away_form_w10, 4),
        "home_goals_avg": round(home_goals_avg, 3),
        "away_goals_avg": round(away_goals_avg, 3),
        "home_goals_conceded_avg": round(home_goals_conceded_avg, 3),
        "away_goals_conceded_avg": round(away_goals_conceded_avg, 3),
        "home_xg_avg": round(home_xg_avg, 3),
        "away_xg_avg": round(away_xg_avg, 3),
        "h2h_home_wins": h2h_home_wins,
        "h2h_draws": h2h_draws,
        "h2h_away_wins": h2h_away_wins,
        "days_since_last_match_home": days_home,
        "days_since_last_match_away": days_away,
    }


async def fetch_db_rows(n: int = 5000) -> list[dict]:
    """Try to pull match data from the database as real training samples."""
    try:
        os.environ.setdefault("VIT_DATABASE_URL", "sqlite+aiosqlite:///./vit.db")
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import text

        db_url = os.getenv("VIT_DATABASE_URL", "sqlite+aiosqlite:///./vit.db")
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        rows = []
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT home_odds, draw_odds, away_odds, result
                FROM matches
                WHERE result IS NOT NULL
                  AND home_odds IS NOT NULL
                  AND draw_odds IS NOT NULL
                  AND away_odds IS NOT NULL
                LIMIT :n
            """), {"n": n})
            for r in result.fetchall():
                ho, do, ao, res = r
                outcome_map = {"H": "home", "D": "draw", "A": "away"}
                if res not in outcome_map:
                    continue
                rows.append({
                    "outcome": outcome_map[res],
                    "result": res,
                    "home_odds": float(ho),
                    "draw_odds": float(do),
                    "away_odds": float(ao),
                })
        await engine.dispose()
        return rows
    except Exception as e:
        logger.warning(f"DB fetch failed: {e}")
        return []


def generate_dataset(n_samples: int, seed: int = 42) -> pd.DataFrame:
    """Generate a full synthetic dataset of n_samples matches."""
    rng = np.random.default_rng(seed)
    rows = []

    for i in range(n_samples):
        league = LEAGUES[i % len(LEAGUES)]
        config = LEAGUE_CONFIGS[league]
        row = generate_match_row(rng, config)
        row["league"] = league
        row["match_id"] = i + 1
        rows.append(row)

    df = pd.DataFrame(rows)

    # Outcome distribution check
    dist = df["outcome"].value_counts(normalize=True)
    logger.info(f"Outcome distribution — Home: {dist.get('home', 0):.1%}, Draw: {dist.get('draw', 0):.1%}, Away: {dist.get('away', 0):.1%}")

    return df


def main():
    parser = argparse.ArgumentParser(description="VIT Network Training Data Generator")
    parser.add_argument("--samples", type=int, default=5000, help="Number of synthetic samples to generate")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Output CSV path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--with-db", action="store_true", help="Also pull real matches from the database")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    # Pull real data if requested
    if args.with_db:
        logger.info("Fetching real matches from database...")
        real_rows = asyncio.run(fetch_db_rows(n=10000))
        if real_rows:
            logger.info(f"  Got {len(real_rows)} real matches")
            rows.extend(real_rows)
        else:
            logger.info("  No real matches found, using synthetic only")

    # Generate synthetic data
    logger.info(f"Generating {args.samples} synthetic match samples (seed={args.seed})...")
    df_synthetic = generate_dataset(args.samples, seed=args.seed)

    if rows:
        df_real = pd.DataFrame(rows)
        df = pd.concat([df_real, df_synthetic], ignore_index=True)
        logger.info(f"Combined: {len(df_real)} real + {len(df_synthetic)} synthetic = {len(df)} total rows")
    else:
        df = df_synthetic
        logger.info(f"Synthetic only: {len(df)} rows")

    df.to_csv(output_path, index=False)
    logger.info(f"Saved training data to {output_path}")
    logger.info(f"Columns: {list(df.columns)}")
    logger.info(f"Shape: {df.shape}")
    logger.info(f"\nNext step: python scripts/train_models.py")


if __name__ == "__main__":
    main()
