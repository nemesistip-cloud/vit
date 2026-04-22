#!/usr/bin/env python3
"""End-to-end pipeline: Model → Predictions → Strategy → Backtest → Profit.

Chains the building blocks built in earlier steps into one runnable flow:

    1. MODEL        load model output (or use the built-in demo model)
    2. PREDICTIONS  attach edges, odds and recommended stakes to each pick
    3. STRATEGY     filter picks via bet side / edge / odds rules
    4. BACKTEST     simulate bankroll growth from 1 unit using the picks
    5. PROFIT       report final bankroll, ROI, drawdown

Usage:
    python pipeline.py                              # demo end-to-end
    python pipeline.py --predictions bets.csv
    python pipeline.py --predictions bets.json --side home --min-edge 0.03 \\
                       --min-odds 1.7 --max-odds 3.0 --bankroll 1.0
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from app.services.bet_filter import BetFilter, evaluate, filter_bets
from scripts.bankroll_backtest import run_backtest, _demo_dataset


def _load_predictions(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text())
        if isinstance(data, dict) and "bets" in data:
            data = data["bets"]
        return [dict(r) for r in data]
    if path.suffix.lower() == ".csv":
        with path.open(newline="") as fh:
            return list(csv.DictReader(fh))
    raise ValueError(f"Unsupported file type: {path.suffix} (use .csv or .json)")


def _ensure_recommended_stake(bets: list[dict], default_frac: float = 0.02) -> list[dict]:
    """Attach `recommended_stake` to any bet that doesn't carry one."""
    out = []
    for b in bets:
        b = dict(b)
        if b.get("recommended_stake") in (None, "", 0):
            b["recommended_stake"] = default_frac
        out.append(b)
    return out


def _print_section(title: str) -> None:
    print(f"\n── {title} " + "─" * (60 - len(title)))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Model → Predictions → Strategy → Backtest → Profit")
    p.add_argument("--predictions", help="Path to bet/prediction dataset (.csv or .json). "
                                          "Omit to use the built-in demo model.")
    p.add_argument("--side", action="append", help="Strategy: filter bet side (repeatable)")
    p.add_argument("--min-edge", type=float, help="Strategy: minimum edge (fraction)")
    p.add_argument("--max-edge", type=float, help="Strategy: maximum edge (fraction)")
    p.add_argument("--min-odds", type=float, help="Strategy: minimum decimal odds")
    p.add_argument("--max-odds", type=float, help="Strategy: maximum decimal odds")
    p.add_argument("--bankroll", type=float, default=1.0, help="Starting bankroll (default 1.0)")
    p.add_argument("--default-stake", type=float, default=0.02,
                   help="Fallback recommended_stake fraction if missing (default 0.02 = 2%%)")
    p.add_argument("--json", action="store_true", help="Emit JSON only")
    args = p.parse_args(argv)

    # ── 1. MODEL → PREDICTIONS ──────────────────────────────────────
    if args.predictions:
        path = Path(args.predictions)
        if not path.exists():
            print(f"error: predictions file not found: {path}", file=sys.stderr)
            return 2
        predictions = _load_predictions(path)
        model_label = f"file:{path.name}"
    else:
        predictions = _demo_dataset()
        model_label = "demo-model-v1"

    predictions = _ensure_recommended_stake(predictions, default_frac=args.default_stake)

    # ── 2. STRATEGY ────────────────────────────────────────────────
    strat = BetFilter(
        bet_sides=args.side, min_edge=args.min_edge, max_edge=args.max_edge,
        min_odds=args.min_odds, max_odds=args.max_odds,
    )
    selected = filter_bets(predictions, strat)
    perf = evaluate(predictions, strat)         # pre-backtest summary on filtered set

    # ── 3. BACKTEST ────────────────────────────────────────────────
    bt = run_backtest(selected, initial_bankroll=args.bankroll)

    # ── 4. PROFIT REPORT ───────────────────────────────────────────
    payload = {
        "model": model_label,
        "predictions_total": len(predictions),
        "strategy": {
            "bet_sides": args.side,
            "min_edge": args.min_edge, "max_edge": args.max_edge,
            "min_odds": args.min_odds, "max_odds": args.max_odds,
        },
        "selected_bets": len(selected),
        "performance": {
            "win_rate_pct": round(perf.win_rate * 100, 2),
            "avg_odds": perf.avg_odds,
            "avg_edge_pct": round(perf.avg_edge * 100, 2),
        },
        "backtest": bt.summary(),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    _print_section("1. MODEL → PREDICTIONS")
    print(f"  Source                : {model_label}")
    print(f"  Predictions loaded    : {len(predictions)}")
    if predictions:
        sample = predictions[0]
        keys = [k for k in ("bet_side", "odds", "edge", "recommended_stake", "result") if k in sample]
        print(f"  Sample fields         : {keys}")

    _print_section("2. STRATEGY")
    print(f"  Sides                 : {args.side or 'any'}")
    print(f"  Edge range            : "
          f"{args.min_edge if args.min_edge is not None else '−∞'} .. "
          f"{args.max_edge if args.max_edge is not None else '+∞'}")
    print(f"  Odds range            : "
          f"{args.min_odds if args.min_odds is not None else '−∞'} .. "
          f"{args.max_odds if args.max_odds is not None else '+∞'}")
    print(f"  Selected after filter : {len(selected)}  ({len(selected)}/{len(predictions)} predictions kept)")
    print(f"  Pre-backtest win rate : {perf.win_rate * 100:.2f}%   avg odds {perf.avg_odds:.2f}   avg edge {perf.avg_edge * 100:.2f}%")

    _print_section("3. BACKTEST (bankroll simulation)")
    s = bt.summary()
    print(f"  Initial bankroll      : {s['initial_bankroll']:.4f} units")
    print(f"  Final bankroll        : {s['final_bankroll']:.4f} units")
    print(f"  Bets played           : {s['total_bets']}  (W {s['wins']} / L {s['losses']} / V {s['voids']})")
    print(f"  Total staked          : {s['total_staked']:.4f} units")
    print(f"  Max bankroll (peak)   : {s['max_bankroll']:.4f}")
    print(f"  Max drawdown          : {s['max_drawdown_pct']:.2f}%   ({s['max_drawdown_abs']:.4f} units)")

    _print_section("4. PROFIT")
    profit = s["cumulative_profit"]
    verdict = "PROFITABLE ✓" if profit > 0 else ("BREAK-EVEN" if profit == 0 else "LOSS ✗")
    print(f"  Cumulative profit     : {profit:+.4f} units")
    print(f"  Growth                : {s['growth_pct']:+.2f}%")
    print(f"  ROI (profit/staked)   : {s['roi_pct']:+.2f}%")
    print(f"  Win rate              : {s['win_rate_pct']:.2f}%")
    print(f"  Verdict               : {verdict}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
