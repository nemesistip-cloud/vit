#!/usr/bin/env python3
"""Strategy explorer.

Sweeps a grid of edge × odds × side filters across a bet dataset and ranks
the resulting strategies by ROI, so you can find which filter combination
historically produced the strongest returns.

Usage:
    python strategy.py                         # uses built-in demo dataset
    python strategy.py path/to/bets.csv
    python strategy.py bets.json --top 10 --min-bets 20
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from itertools import product
from pathlib import Path

from app.services.bet_filter import BetFilter, evaluate
from scripts.bankroll_backtest import _demo_dataset


# Grid of strategy filters to test
SIDES = [None, ["home"], ["away"], ["draw"], ["home", "away"]]
EDGE_BUCKETS = [
    (None, None), (0.01, None), (0.03, None), (0.05, None), (0.08, None),
]
ODDS_BUCKETS = [
    (None, None), (1.50, 2.00), (2.00, 2.50), (2.50, 3.50), (1.70, 3.00),
]


def _load(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text())
        if isinstance(data, dict) and "bets" in data:
            data = data["bets"]
        return [dict(r) for r in data]
    if path.suffix.lower() == ".csv":
        with path.open(newline="") as fh:
            return list(csv.DictReader(fh))
    raise ValueError(f"Unsupported file type: {path.suffix}")


def _label(sides, edge_lo, edge_hi, odds_lo, odds_hi) -> str:
    parts = []
    parts.append("side=" + (",".join(sides) if sides else "any"))
    if edge_lo is not None or edge_hi is not None:
        parts.append(f"edge=[{edge_lo or 0:.2f}..{edge_hi or '∞'}]")
    else:
        parts.append("edge=any")
    if odds_lo is not None or odds_hi is not None:
        parts.append(f"odds=[{odds_lo or 0:.2f}..{odds_hi or '∞'}]")
    else:
        parts.append("odds=any")
    return "  ".join(parts)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Strategy filter sweeper.")
    p.add_argument("dataset", nargs="?", help="Path to .csv or .json (omit for demo)")
    p.add_argument("--top", type=int, default=10, help="Show top-N strategies by ROI")
    p.add_argument("--min-bets", type=int, default=3,
                   help="Skip strategies with fewer bets than this")
    p.add_argument("--json", action="store_true", help="Emit JSON only")
    args = p.parse_args(argv)

    if args.dataset:
        path = Path(args.dataset)
        if not path.exists():
            print(f"error: not found: {path}", file=sys.stderr)
            return 2
        bets = _load(path)
        source = str(path)
    else:
        bets = _demo_dataset()
        source = "(built-in demo dataset)"

    rankings = []
    for sides, (edge_lo, edge_hi), (odds_lo, odds_hi) in product(SIDES, EDGE_BUCKETS, ODDS_BUCKETS):
        f = BetFilter(
            bet_sides=sides, min_edge=edge_lo, max_edge=edge_hi,
            min_odds=odds_lo, max_odds=odds_hi,
        )
        r = evaluate(bets, f)
        if r.total_bets < args.min_bets:
            continue
        rankings.append({
            "label": _label(sides, edge_lo, edge_hi, odds_lo, odds_hi),
            "bets": r.total_bets,
            "win_rate_pct": round(r.win_rate * 100, 2),
            "roi_pct": round(r.roi * 100, 2),
            "profit": round(r.profit, 4),
            "avg_odds": round(r.avg_odds, 2),
        })

    rankings.sort(key=lambda x: x["roi_pct"], reverse=True)
    top = rankings[: args.top]

    if args.json:
        print(json.dumps({"source": source, "tested": len(rankings), "top": top}, indent=2))
        return 0

    print(f"\n=== Strategy Sweep — {source} ===")
    print(f"  Strategies tested (>= {args.min_bets} bets): {len(rankings)}")
    if not top:
        print("  No strategies met the minimum bet count. Try lowering --min-bets.")
        return 0
    print(f"\n  {'#':>2}  {'BETS':>5}  {'WR%':>7}  {'ROI%':>8}  {'PROFIT':>9}  {'AVG_ODDS':>9}  STRATEGY")
    for i, s in enumerate(top, 1):
        print(f"  {i:>2}  {s['bets']:>5}  {s['win_rate_pct']:>7.2f}  "
              f"{s['roi_pct']:>+8.2f}  {s['profit']:>+9.4f}  {s['avg_odds']:>9.2f}  {s['label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
