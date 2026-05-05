# services/ml_service/simulation_engine.py
# VIT Sports Intelligence — Beast Mode Simulation Engine
# 3-Tier Synthetic Match Generator
# Tier 1: Base (Poisson + noise)         — 60% of total
# Tier 2: Context (form, fatigue)        — 30% of total
# Tier 3: Chaos (red cards, anomalies)   — 10% of total

import json
import logging
import math
import os
import random
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Team pool (60 realistic teams with varied profiles) ──────────────────────
def _build_team_pool(seed: int = 42) -> List[Dict]:
    rng = random.Random(seed)
    tiers = [
        ("Elite",    1.80, 2.20, 0.55, 0.80, 12),   # attack_lo, attack_hi, def_lo, def_hi, count
        ("Strong",   1.40, 1.80, 0.75, 1.05, 18),
        ("Mid",      1.10, 1.50, 0.95, 1.25, 18),
        ("Lower",    0.80, 1.20, 1.15, 1.50, 12),
    ]
    teams = []
    for tier_name, a_lo, a_hi, d_lo, d_hi, count in tiers:
        for i in range(count):
            teams.append({
                "name": f"{tier_name}_{i:02d}",
                "tier": tier_name,
                "attack":  round(rng.uniform(a_lo, a_hi), 3),
                "defense": round(rng.uniform(d_lo, d_hi), 3),
                "home_adv": round(rng.uniform(1.10, 1.28), 3),
            })
    rng.shuffle(teams)
    return teams


TEAM_POOL: List[Dict] = _build_team_pool()
LEAGUES = [
    "premier_league",
    "la_liga",
    "bundesliga",
    "serie_a",
    "ligue_1",
    "championship",
    "eredivisie",
    "primeira_liga",
    "scottish_premiership",
    "belgian_pro_league",
]

PRESET_SIZES = {
    "dev":        10_000,
    "standard":  100_000,
    "large":     500_000,
    "full":    1_000_000,
}


# ── Core Poisson simulation ───────────────────────────────────────────────────
def _poisson_goals(lam: float, rng: random.Random) -> int:
    lam = max(0.05, lam)
    L = math.exp(-lam)
    k, p = 0, 1.0
    while p > L:
        k += 1
        p *= rng.random()
    return k - 1


def _outcome(home: int, away: int) -> str:
    if home > away: return "H"
    if home < away: return "A"
    return "D"


# ── Tier 1: Base (pure Poisson + noise) ──────────────────────────────────────
def _simulate_tier1(home: Dict, away: Dict, rng: random.Random) -> Dict:
    noise = rng.gauss(1.0, 0.08)
    lam_h = max(0.3, home["attack"] * away["defense"] * home["home_adv"] * noise)
    lam_a = max(0.3, away["attack"] * home["defense"] * rng.gauss(1.0, 0.08))
    gh = _poisson_goals(lam_h, rng)
    ga = _poisson_goals(lam_a, rng)
    return {
        "tier": 1,
        "home_attack": home["attack"], "away_attack": away["attack"],
        "home_defense": home["defense"], "away_defense": away["defense"],
        "home_adv": home["home_adv"],
        "home_form": 1.0, "away_form": 1.0,
        "home_fatigue": 1.0, "away_fatigue": 1.0,
        "red_card_home": 0, "red_card_away": 0,
        "lambda_home": round(lam_h, 3), "lambda_away": round(lam_a, 3),
        "home_goals": gh, "away_goals": ga,
    }


# ── Tier 2: Context (form + fatigue multipliers) ──────────────────────────────
def _simulate_tier2(home: Dict, away: Dict, rng: random.Random) -> Dict:
    home_form    = rng.uniform(0.82, 1.18)
    away_form    = rng.uniform(0.82, 1.18)
    home_fatigue = rng.uniform(0.90, 1.00)
    away_fatigue = rng.uniform(0.90, 1.00)

    lam_h = max(0.3, home["attack"] * away["defense"] * home["home_adv"] * home_form * home_fatigue)
    lam_a = max(0.3, away["attack"] * home["defense"] * away_form * away_fatigue)
    gh = _poisson_goals(lam_h, rng)
    ga = _poisson_goals(lam_a, rng)
    return {
        "tier": 2,
        "home_attack": home["attack"], "away_attack": away["attack"],
        "home_defense": home["defense"], "away_defense": away["defense"],
        "home_adv": home["home_adv"],
        "home_form": round(home_form, 3), "away_form": round(away_form, 3),
        "home_fatigue": round(home_fatigue, 3), "away_fatigue": round(away_fatigue, 3),
        "red_card_home": 0, "red_card_away": 0,
        "lambda_home": round(lam_h, 3), "lambda_away": round(lam_a, 3),
        "home_goals": gh, "away_goals": ga,
    }


# ── Tier 3: Chaos (red cards, injuries, anomalies) ────────────────────────────
def _simulate_tier3(home: Dict, away: Dict, rng: random.Random) -> Dict:
    base = _simulate_tier2(home, away, rng)
    base["tier"] = 3

    # Red cards (3% chance per team — reduces attack by 30%)
    rc_home = 1 if rng.random() < 0.03 else 0
    rc_away = 1 if rng.random() < 0.03 else 0
    base["red_card_home"] = rc_home
    base["red_card_away"] = rc_away

    # Key injury (5% chance — reduces λ by 20%)
    injury_home = 1 if rng.random() < 0.05 else 0
    injury_away = 1 if rng.random() < 0.05 else 0

    # Momentum shift (late goal bias — 8% chance of bonus goal)
    lam_h = base["lambda_home"] * (0.70 if rc_home else 1.0) * (0.80 if injury_home else 1.0)
    lam_a = base["lambda_away"] * (0.70 if rc_away else 1.0) * (0.80 if injury_away else 1.0)
    lam_h = max(0.1, lam_h)
    lam_a = max(0.1, lam_a)

    gh = _poisson_goals(lam_h, rng)
    ga = _poisson_goals(lam_a, rng)

    # Momentum: leading team late goal
    if rng.random() < 0.08:
        if gh > ga: gh += 1
        elif ga > gh: ga += 1

    # Anomaly: extreme scorelines (2% chance)
    if rng.random() < 0.02:
        if rng.random() < 0.5:
            gh += rng.randint(2, 4)
        else:
            ga += rng.randint(2, 4)

    base["lambda_home"] = round(lam_h, 3)
    base["lambda_away"] = round(lam_a, 3)
    base["home_goals"] = gh
    base["away_goals"] = ga
    return base


_TIER_FNS = {1: _simulate_tier1, 2: _simulate_tier2, 3: _simulate_tier3}


# ── Market odds helper (inline — avoids circular import) ─────────────────────
def _true_probs(lam_h: float, lam_a: float, max_goals: int = 8) -> Tuple[float, float, float]:
    """Compute exact 1X2 probabilities from Poisson parameters."""
    ph = pd = pa = 0.0
    for g in range(max_goals + 1):
        p_g_home = math.exp(-lam_h) * lam_h**g / math.factorial(g)
        for h in range(max_goals + 1):
            p_g_away = math.exp(-lam_a) * lam_a**h / math.factorial(h)
            p = p_g_home * p_g_away
            if g > h: ph += p
            elif g == h: pd += p
            else: pa += p
    total = ph + pd + pa
    if total <= 0: return 1/3, 1/3, 1/3
    return ph / total, pd / total, pa / total


def _make_market_odds(hp: float, dp: float, ap: float,
                      margin: float, bias: float, noise_sd: float,
                      rng: random.Random) -> Dict[str, float]:
    """Convert true probs to decimal odds with margin, bias, and noise."""
    # Inflate popular teams slightly (bias toward home)
    hp_adj = hp * (1 + bias)
    dp_adj = dp
    ap_adj = ap * (1 - bias * 0.3)
    total = hp_adj + dp_adj + ap_adj
    if total <= 0: total = 1.0
    hp_adj /= total; dp_adj /= total; ap_adj /= total

    # Apply bookmaker margin (overround)
    marg = 1 + margin
    home_odds = max(1.01, (1 / (hp_adj * marg)) * rng.gauss(1.0, noise_sd))
    draw_odds = max(1.01, (1 / (dp_adj * marg)) * rng.gauss(1.0, noise_sd))
    away_odds = max(1.01, (1 / (ap_adj * marg)) * rng.gauss(1.0, noise_sd))
    return {"home": round(home_odds, 2), "draw": round(draw_odds, 2), "away": round(away_odds, 2)}


def _vig_free_probs(odds: Dict[str, float]) -> Dict[str, float]:
    h, d, a = 1/odds["home"], 1/odds["draw"], 1/odds["away"]
    total = h + d + a
    if total <= 0: total = 1.0
    return {"home": round(h/total, 4), "draw": round(d/total, 4), "away": round(a/total, 4)}


# ── Main SimulationEngine ─────────────────────────────────────────────────────
class SimulationEngine:
    """
    3-tier football match simulation engine.

    Usage:
        engine = SimulationEngine(total_matches=100_000, seed=42)
        for chunk in engine.generate(chunk_size=10_000, progress_cb=None):
            # chunk is a list of match dicts
            process(chunk)

    Tier split (configurable):
        tier1_frac: 0.60   (base — pure Poisson)
        tier2_frac: 0.30   (context — form/fatigue)
        tier3_frac: 0.10   (chaos — red cards, anomalies)
    """

    def __init__(
        self,
        total_matches: int = 100_000,
        seed: int = 42,
        tier1_frac: float = 0.60,
        tier2_frac: float = 0.30,
        tier3_frac: float = 0.10,
        market_margin: float = 0.075,
        market_bias: float = 0.015,
        market_noise_sd: float = 0.025,
        team_pool: Optional[List[Dict]] = None,
        leagues: Optional[List[str]] = None,
    ):
        self.total_matches  = total_matches
        self.seed           = seed
        self.tier1_frac     = tier1_frac
        self.tier2_frac     = tier2_frac
        self.tier3_frac     = tier3_frac
        self.market_margin  = market_margin
        self.market_bias    = market_bias
        self.market_noise_sd = market_noise_sd
        self.team_pool      = team_pool or TEAM_POOL
        self.leagues        = leagues or LEAGUES

        n = total_matches
        self._tier_counts = {
            1: int(n * tier1_frac),
            2: int(n * tier2_frac),
            3: n - int(n * tier1_frac) - int(n * tier2_frac),
        }

    # ── Internal match builder ────────────────────────────────────────────────
    def _build_match(self, idx: int, tier: int, rng: random.Random) -> Dict[str, Any]:
        n = len(self.team_pool)
        hi = rng.randint(0, n - 1)
        ai = rng.randint(0, n - 2)
        if ai >= hi: ai += 1  # ensure different teams

        home = self.team_pool[hi]
        away = self.team_pool[ai]

        sim_fn = _TIER_FNS[tier]
        sim = sim_fn(home, away, rng)

        gh = sim["home_goals"]
        ga = sim["away_goals"]
        total = gh + ga
        result = _outcome(gh, ga)

        hp, dp, ap = _true_probs(sim["lambda_home"], sim["lambda_away"])

        # Market odds (opening)
        odds = _make_market_odds(hp, dp, ap, self.market_margin, self.market_bias, self.market_noise_sd, rng)
        vfp = _vig_free_probs(odds)

        # Simulated closing odds (slightly narrower margin — market "informed")
        closing_margin = self.market_margin * 0.85
        closing_odds = _make_market_odds(hp, dp, ap, closing_margin, self.market_bias * 0.7, self.market_noise_sd * 0.5, rng)

        return {
            "match_id": f"sim_t{tier}_{idx:08d}",
            "tier": tier,
            "home_team": home["name"],
            "away_team": away["name"],
            "league": rng.choice(self.leagues),
            "home_goals": gh,
            "away_goals": ga,
            "result": result,
            "total_goals": total,
            "over_25": int(total > 2.5),
            "over_15": int(total > 1.5),
            "under_25": int(total <= 2.5),
            "btts": int(gh > 0 and ga > 0),
            "home_attack": home["attack"],
            "away_attack": away["attack"],
            "home_defense": home["defense"],
            "away_defense": away["defense"],
            "home_adv": sim.get("home_adv", home["home_adv"]),
            "home_form": sim.get("home_form", 1.0),
            "away_form": sim.get("away_form", 1.0),
            "home_fatigue": sim.get("home_fatigue", 1.0),
            "away_fatigue": sim.get("away_fatigue", 1.0),
            "red_card_home": sim.get("red_card_home", 0),
            "red_card_away": sim.get("red_card_away", 0),
            "lambda_home": sim["lambda_home"],
            "lambda_away": sim["lambda_away"],
            "true_home_prob": round(hp, 4),
            "true_draw_prob": round(dp, 4),
            "true_away_prob": round(ap, 4),
            "market_odds": odds,
            "closing_odds": closing_odds,
            "vig_free_probs": vfp,
            "market_prob_home": vfp["home"],
            "market_prob_draw": vfp["draw"],
            "market_prob_away": vfp["away"],
            "model_predictions": {},
            "actual_outcome": result,
        }

    # ── Generator (chunked — memory efficient) ────────────────────────────────
    def generate(
        self,
        chunk_size: int = 5_000,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> Generator[List[Dict], None, None]:
        """
        Yields chunks of simulated match dicts.
        Total matches = sum of tier counts.
        """
        rng = random.Random(self.seed)

        # Build tier schedule (interleaved for representativeness)
        schedule: List[Tuple[int, int]] = []  # (global_idx, tier)
        global_idx = 0
        for tier, count in self._tier_counts.items():
            for _ in range(count):
                schedule.append((global_idx, tier))
                global_idx += 1
        rng.shuffle(schedule)

        chunk: List[Dict] = []
        for i, (gidx, tier) in enumerate(schedule):
            chunk.append(self._build_match(gidx, tier, rng))
            if len(chunk) >= chunk_size:
                if progress_cb:
                    progress_cb(i + 1, self.total_matches)
                yield chunk
                chunk = []

        if chunk:
            if progress_cb:
                progress_cb(self.total_matches, self.total_matches)
            yield chunk

    # ── Generate and save to JSONL file ───────────────────────────────────────
    def generate_to_file(
        self,
        out_path: str,
        chunk_size: int = 5_000,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Stream-generate all matches to a JSONL file.
        Returns stats about the generated dataset.
        """
        os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else ".", exist_ok=True)
        t0 = time.monotonic()
        total_written = 0
        tier_counts = {1: 0, 2: 0, 3: 0}
        outcomes = {"H": 0, "D": 0, "A": 0}

        with open(out_path, "w") as f:
            for chunk in self.generate(chunk_size=chunk_size, progress_cb=progress_cb):
                for match in chunk:
                    f.write(json.dumps(match) + "\n")
                    tier_counts[match["tier"]] = tier_counts.get(match["tier"], 0) + 1
                    outcomes[match["result"]] = outcomes.get(match["result"], 0) + 1
                total_written += len(chunk)

        elapsed = round(time.monotonic() - t0, 2)
        size_mb = round(os.path.getsize(out_path) / 1_048_576, 2)
        logger.info(f"SimulationEngine: wrote {total_written:,} matches to {out_path} ({size_mb} MB) in {elapsed}s")
        return {
            "total_matches": total_written,
            "tier_counts": tier_counts,
            "outcome_distribution": outcomes,
            "elapsed_s": elapsed,
            "size_mb": size_mb,
            "output_path": out_path,
        }

    # ── Generate in-memory (smaller datasets only) ────────────────────────────
    def generate_in_memory(
        self,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict]:
        """
        Generate all matches in memory. Only use for total_matches < 50_000.
        For larger datasets, use generate_to_file().
        """
        if self.total_matches > 50_000:
            logger.warning(f"SimulationEngine: generating {self.total_matches:,} matches in memory — consider generate_to_file()")
        matches = []
        for chunk in self.generate(chunk_size=5_000, progress_cb=progress_cb):
            matches.extend(chunk)
        return matches

    # ── Load generated dataset (JSONL) ────────────────────────────────────────
    @staticmethod
    def load_jsonl(path: str, limit: Optional[int] = None) -> List[Dict]:
        """Load matches from a JSONL file (optionally limited)."""
        matches = []
        with open(path) as f:
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break
                line = line.strip()
                if line:
                    try:
                        matches.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return matches

    # ── Dataset stats ──────────────────────────────────────────────────────────
    @staticmethod
    def stats(matches: List[Dict]) -> Dict[str, Any]:
        if not matches:
            return {}
        goals = [m["total_goals"] for m in matches]
        outcomes = {"H": 0, "D": 0, "A": 0}
        tiers = {1: 0, 2: 0, 3: 0}
        for m in matches:
            outcomes[m.get("result", "D")] = outcomes.get(m.get("result", "D"), 0) + 1
            tiers[m.get("tier", 1)] = tiers.get(m.get("tier", 1), 0) + 1
        return {
            "total": len(matches),
            "avg_goals": round(float(np.mean(goals)), 3),
            "std_goals": round(float(np.std(goals)), 3),
            "outcome_pct": {k: round(v / len(matches) * 100, 1) for k, v in outcomes.items()},
            "tier_distribution": tiers,
            "over_25_pct": round(sum(m.get("over_25", 0) for m in matches) / len(matches) * 100, 1),
            "btts_pct": round(sum(m.get("btts", 0) for m in matches) / len(matches) * 100, 1),
        }
