#!/usr/bin/env python3
"""Bankroll backtester.

Simulates a bankroll starting from 1.0 unit, walking through a chronologically
ordered dataset of bets. Each row is expected to provide a `recommended_stake`
(fraction of the *current* bankroll, e.g. 0.02 = 2%) along with `odds` and
`result`. The script tracks cumulative profit and reports final bankroll, ROI,
and the worst peak-to-trough drawdown.

Usage
-----
    python scripts/bankroll_backtest.py path/to/bets.csv
    python scripts/bankroll_backtest.py path/to/bets.json
    python scripts/bankroll_backtest.py --demo

CSV / JSON columns
------------------
Required:
    odds                decimal odds, e.g. 2.10
    result              "won" | "lost" | "void" (also accepts "win"/"loss",
                        boolean `won`, or signed `pnl`)

One of:
    recommended_stake   fraction of current bankroll (preferred), e.g. 0.025
    stake_fraction      alias for recommended_stake
    stake_units         absolute units (used as-is, ignores bankroll fraction)

Optional:
    bet_side, edge, placed_at  — passed through, useful for filtering upstream
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

INITIAL_BANKROLL = 1.0
DEFAULT_FALLBACK_STAKE_FRACTION = 0.01     # 1% if a row has no recommended_stake


# ── Data containers ───────────────────────────────────────────────────

@dataclass
class StepRecord:
    index: int
    bankroll_before: float
    stake: float
    odds: float
    outcome: str
    pnl: float
    bankroll_after: float
    cumulative_profit: float


@dataclass
class BacktestResult:
    initial_bankroll: float = INITIAL_BANKROLL
    final_bankroll: float = INITIAL_BANKROLL
    total_bets: int = 0
    settled_bets: int = 0
    wins: int = 0
    losses: int = 0
    voids: int = 0
    total_staked: float = 0.0
    cumulative_profit: float = 0.0
    roi: float = 0.0                          # profit / total_staked
    growth: float = 0.0                       # final / initial - 1
    max_bankroll: float = INITIAL_BANKROLL
    max_drawdown: float = 0.0                 # worst (peak - trough) / peak
    max_drawdown_abs: float = 0.0             # worst absolute drop in units
    win_rate: float = 0.0
    avg_odds: float = 0.0
    history: list[StepRecord] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "initial_bankroll": round(self.initial_bankroll, 6),
            "final_bankroll": round(self.final_bankroll, 6),
            "cumulative_profit": round(self.cumulative_profit, 6),
            "roi_pct": round(self.roi * 100, 4),
            "growth_pct": round(self.growth * 100, 4),
            "max_drawdown_pct": round(self.max_drawdown * 100, 4),
            "max_drawdown_abs": round(self.max_drawdown_abs, 6),
            "max_bankroll": round(self.max_bankroll, 6),
            "total_bets": self.total_bets,
            "settled_bets": self.settled_bets,
            "wins": self.wins,
            "losses": self.losses,
            "voids": self.voids,
            "win_rate_pct": round(self.win_rate * 100, 4),
            "avg_odds": round(self.avg_odds, 4),
            "total_staked": round(self.total_staked, 6),
        }


# ── Result resolution ─────────────────────────────────────────────────

def _resolve_outcome(bet: dict) -> str:
    r = bet.get("result")
    if r is not None:
        s = str(r).strip().lower()
        if s in ("won", "win", "w", "1", "true"):  return "won"
        if s in ("lost", "loss", "l", "0", "false"): return "lost"
        if s in ("void", "push", "refund", "cancelled", "canceled"): return "void"
    won = bet.get("won")
    if won is True:  return "won"
    if won is False: return "lost"
    pnl = bet.get("pnl")
    if pnl is not None:
        try:
            v = float(pnl)
            if v > 0:  return "won"
            if v < 0:  return "lost"
            return "void"
        except (TypeError, ValueError):
            pass
    return "pending"


def _resolve_stake(bet: dict, bankroll: float) -> float:
    """Resolve stake (in units) for the current bet given the current bankroll."""
    if bet.get("stake_units") is not None:
        try:
            return max(0.0, float(bet["stake_units"]))
        except (TypeError, ValueError):
            pass
    frac = bet.get("recommended_stake", bet.get("stake_fraction"))
    if frac is None:
        frac = DEFAULT_FALLBACK_STAKE_FRACTION
    try:
        frac = float(frac)
    except (TypeError, ValueError):
        frac = DEFAULT_FALLBACK_STAKE_FRACTION
    # Sanity bounds: stake fraction must be in (0, 1]
    frac = max(0.0, min(1.0, frac))
    return bankroll * frac


# ── Core simulation ───────────────────────────────────────────────────

def run_backtest(
    bets: Iterable[dict],
    initial_bankroll: float = INITIAL_BANKROLL,
    skip_pending: bool = True,
) -> BacktestResult:
    """Walk through `bets` in order, simulating bankroll growth."""
    res = BacktestResult(
        initial_bankroll=initial_bankroll,
        final_bankroll=initial_bankroll,
        max_bankroll=initial_bankroll,
    )
    bankroll = initial_bankroll
    peak = initial_bankroll
    odds_sum = 0.0

    for i, bet in enumerate(bets):
        outcome = _resolve_outcome(bet)
        if outcome == "pending" and skip_pending:
            continue

        try:
            odds = float(bet.get("odds", 0) or 0)
        except (TypeError, ValueError):
            odds = 0.0
        if odds <= 0:
            continue

        stake = _resolve_stake(bet, bankroll)
        if stake <= 0 or stake > bankroll:
            stake = min(stake, bankroll)
            if stake <= 0:
                continue

        bankroll_before = bankroll

        if outcome == "won":
            pnl = stake * (odds - 1.0)
            res.wins += 1
            res.settled_bets += 1
            res.total_staked += stake
        elif outcome == "lost":
            pnl = -stake
            res.losses += 1
            res.settled_bets += 1
            res.total_staked += stake
        else:  # void — stake refunded
            pnl = 0.0
            res.voids += 1
            res.total_staked += stake

        bankroll += pnl
        res.cumulative_profit += pnl
        odds_sum += odds
        res.total_bets += 1

        # Drawdown tracking
        if bankroll > peak:
            peak = bankroll
        drop_abs = peak - bankroll
        drop_pct = drop_abs / peak if peak > 0 else 0.0
        if drop_pct > res.max_drawdown:
            res.max_drawdown = drop_pct
        if drop_abs > res.max_drawdown_abs:
            res.max_drawdown_abs = drop_abs

        res.history.append(StepRecord(
            index=i,
            bankroll_before=round(bankroll_before, 6),
            stake=round(stake, 6),
            odds=round(odds, 4),
            outcome=outcome,
            pnl=round(pnl, 6),
            bankroll_after=round(bankroll, 6),
            cumulative_profit=round(res.cumulative_profit, 6),
        ))

    res.final_bankroll = bankroll
    res.max_bankroll = peak
    res.roi = res.cumulative_profit / res.total_staked if res.total_staked > 0 else 0.0
    res.growth = (bankroll / initial_bankroll) - 1.0 if initial_bankroll > 0 else 0.0
    res.win_rate = res.wins / res.settled_bets if res.settled_bets > 0 else 0.0
    res.avg_odds = odds_sum / res.total_bets if res.total_bets > 0 else 0.0
    return res


# ── Loaders ───────────────────────────────────────────────────────────

def _load_dataset(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text())
        if isinstance(data, dict) and "bets" in data:
            data = data["bets"]
        if not isinstance(data, list):
            raise ValueError("JSON must be a list of bets or {'bets': [...]}")
        return [dict(r) for r in data]
    if suffix == ".csv":
        with path.open(newline="") as fh:
            return list(csv.DictReader(fh))
    raise ValueError(f"Unsupported file type: {suffix} (use .csv or .json)")


def _demo_dataset() -> list[dict]:
    """Reproducible demo: 20 bets, mixed outcomes, 2% recommended stake."""
    import random
    random.seed(42)
    bets = []
    for i in range(20):
        odds = round(random.uniform(1.6, 3.5), 2)
        # 52% win rate to demonstrate a profitable edge
        won = random.random() < 0.52
        bets.append({
            "bet_side": random.choice(["home", "draw", "away"]),
            "odds": odds,
            "edge": round(random.uniform(0.01, 0.08), 4),
            "recommended_stake": 0.02,
            "result": "won" if won else "lost",
        })
    return bets


# ── CLI ───────────────────────────────────────────────────────────────

def _print_report(result: BacktestResult, show_history: bool) -> None:
    s = result.summary()
    print("\n=== Bankroll Backtest ===")
    print(f"  Initial bankroll      : {s['initial_bankroll']:.4f} units")
    print(f"  Final bankroll        : {s['final_bankroll']:.4f} units")
    print(f"  Cumulative profit     : {s['cumulative_profit']:+.4f} units")
    print(f"  Growth                : {s['growth_pct']:+.2f}%")
    print(f"  ROI (profit/staked)   : {s['roi_pct']:+.2f}%")
    print(f"  Max bankroll (peak)   : {s['max_bankroll']:.4f} units")
    print(f"  Max drawdown          : {s['max_drawdown_pct']:.2f}%  ({s['max_drawdown_abs']:.4f} units)")
    print(f"  Bets (total/settled)  : {s['total_bets']} / {s['settled_bets']}")
    print(f"  Wins / Losses / Voids : {s['wins']} / {s['losses']} / {s['voids']}")
    print(f"  Win rate              : {s['win_rate_pct']:.2f}%")
    print(f"  Avg odds              : {s['avg_odds']:.2f}")
    print(f"  Total staked          : {s['total_staked']:.4f} units")
    if show_history:
        print("\n--- Bet-by-bet ---")
        print(f"{'#':>3}  {'side_odds':>10}  {'stake':>8}  {'pnl':>8}  {'bankroll':>10}  {'cum_pnl':>10}")
        for h in result.history:
            print(f"{h.index:>3}  {h.outcome:>5}@{h.odds:>4.2f}  {h.stake:>8.4f}  {h.pnl:>+8.4f}  "
                  f"{h.bankroll_after:>10.4f}  {h.cumulative_profit:>+10.4f}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bankroll backtester (start = 1 unit).")
    p.add_argument("dataset", nargs="?", help="Path to .csv or .json bet dataset")
    p.add_argument("--demo", action="store_true", help="Run with built-in demo dataset")
    p.add_argument("--bankroll", type=float, default=INITIAL_BANKROLL,
                   help=f"Starting bankroll (default {INITIAL_BANKROLL})")
    p.add_argument("--json", action="store_true", help="Output summary as JSON only")
    p.add_argument("--history", action="store_true", help="Print bet-by-bet history")
    args = p.parse_args(argv)

    if args.demo:
        bets = _demo_dataset()
    elif args.dataset:
        path = Path(args.dataset)
        if not path.exists():
            print(f"error: dataset not found: {path}", file=sys.stderr)
            return 2
        bets = _load_dataset(path)
    else:
        p.print_help()
        return 2

    result = run_backtest(bets, initial_bankroll=args.bankroll)

    if args.json:
        print(json.dumps(result.summary(), indent=2))
    else:
        _print_report(result, show_history=args.history)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
