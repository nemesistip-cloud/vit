#!/usr/bin/env python3
"""Performance analyzer.

Loads a bet dataset (CSV / JSON) and reports overall performance —
ROI, win rate, profit, average odds — using `app.services.bet_filter.evaluate`.

Usage:
    python performance.py                       # uses built-in demo dataset
    python performance.py path/to/bets.csv
    python performance.py bets.json --json
    python performance.py bets.csv --side home --min-edge 0.03
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from app.services.bet_filter import BetFilter, evaluate
from scripts.bankroll_backtest import _demo_dataset


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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bet performance analyzer.")
    p.add_argument("dataset", nargs="?", help="Path to .csv or .json (omit for demo)")
    p.add_argument("--side", action="append", help="Filter by bet side (repeatable)")
    p.add_argument("--min-edge", type=float, help="Minimum edge (fraction, e.g. 0.03)")
    p.add_argument("--max-edge", type=float, help="Maximum edge (fraction)")
    p.add_argument("--min-odds", type=float, help="Minimum decimal odds")
    p.add_argument("--max-odds", type=float, help="Maximum decimal odds")
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

    filt = BetFilter(
        bet_sides=args.side, min_edge=args.min_edge, max_edge=args.max_edge,
        min_odds=args.min_odds, max_odds=args.max_odds,
    )
    result = evaluate(bets, filt)
    out = result.to_dict()
    out.pop("bets", None)

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"\n=== Performance Report — {source} ===")
    print(f"  Bets selected         : {out['total_bets']}  (W {out['wins']} / L {out['losses']} / V {out['voids']})")
    print(f"  Win rate              : {out['win_rate'] * 100:.2f}%")
    print(f"  Total staked          : {out['total_staked']:.4f} units")
    print(f"  Profit                : {out['profit']:+.4f} units")
    print(f"  ROI                   : {out['roi'] * 100:+.2f}%")
    print(f"  Yield per bet         : {out['yield_per_bet'] * 100:+.2f}%")
    print(f"  Avg odds              : {out['avg_odds']:.2f}")
    print(f"  Avg edge              : {out['avg_edge'] * 100:.2f}%")
    print(f"  Filter applied        : {out['filter_applied']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
