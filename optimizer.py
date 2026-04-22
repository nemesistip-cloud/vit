#!/usr/bin/env python3
"""Strategy optimizer.

Sweeps a multi-dimensional grid of bet filters AND stake sizes, scores each
candidate on a risk-adjusted composite of ROI / bankroll growth / drawdown,
and returns the single best-performing strategy.

Why this exists (vs. `strategy.py`):
  * `strategy.py`  ranks by flat ROI only — ignores compounding & ruin risk.
  * `optimizer.py` simulates each strategy through `bankroll_backtest`,
    factors in maximum drawdown, and (optionally) holds back a portion of
    the dataset as out-of-sample test data so the winner isn't just the
    most overfit filter combination.

Usage:
    python optimizer.py                              # demo dataset
    python optimizer.py bets.csv
    python optimizer.py bets.json --top 10 --split 0.3 --json
    python optimizer.py bets.csv --score growth --kelly 0.25 0.5 1.0
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, asdict
from itertools import product
from pathlib import Path
from typing import Iterable

from app.services.bet_filter import BetFilter, evaluate, filter_bets
from scripts.bankroll_backtest import _demo_dataset, run_backtest


# ── Search grid ──────────────────────────────────────────────────────
SIDES: list[list[str] | None] = [
    None, ["home"], ["away"], ["draw"],
    ["home", "away"], ["home", "draw"], ["away", "draw"],
]
EDGE_BUCKETS: list[tuple[float | None, float | None]] = [
    (None, None), (0.01, None), (0.03, None), (0.05, None),
    (0.08, None), (0.12, None),
]
ODDS_BUCKETS: list[tuple[float | None, float | None]] = [
    (None, None), (1.40, 2.00), (1.70, 2.50), (2.00, 3.00),
    (2.50, 4.00), (1.50, 3.50),
]
DEFAULT_KELLY_FRACTIONS: list[float] = [0.25, 0.5, 1.0]   # fraction of recommended_stake
START_BANKROLL = 1.0


# ── Composite scoring ────────────────────────────────────────────────
@dataclass
class Strategy:
    label: str
    sides: list[str] | None
    min_edge: float | None
    max_edge: float | None
    min_odds: float | None
    max_odds: float | None
    kelly_fraction: float

    bets: int
    win_rate_pct: float
    roi_pct: float
    profit: float
    avg_odds: float

    final_bankroll: float
    growth_pct: float
    max_drawdown_pct: float
    score: float

    test_bets: int | None = None
    test_roi_pct: float | None = None
    test_growth_pct: float | None = None
    test_max_drawdown_pct: float | None = None


def _composite_score(roi_pct: float, growth_pct: float, max_dd_pct: float, bets: int) -> float:
    """Risk-adjusted score combining ROI, compound growth, drawdown penalty
    and a small-sample shrinkage so 3-bet strategies don't dominate."""
    if bets <= 0:
        return -math.inf
    dd_penalty = 1.0 + (max_dd_pct / 100.0)        # 50% DD ⇒ ÷1.5
    raw = (roi_pct + growth_pct) / 2.0
    shrink = bets / (bets + 10.0)                  # bayesian-ish shrink toward 0
    return round((raw / dd_penalty) * shrink, 4)


# ── IO helpers ───────────────────────────────────────────────────────
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


def _label(sides, edge_lo, edge_hi, odds_lo, odds_hi, kelly) -> str:
    side_part = "side=" + (",".join(sides) if sides else "any")
    edge_part = (
        f"edge=[{edge_lo:.2f}..{('%.2f' % edge_hi) if edge_hi else 'inf'}]"
        if edge_lo is not None or edge_hi is not None else "edge=any"
    )
    odds_part = (
        f"odds=[{odds_lo:.2f}..{('%.2f' % odds_hi) if odds_hi else 'inf'}]"
        if odds_lo is not None or odds_hi is not None else "odds=any"
    )
    return f"{side_part}  {edge_part}  {odds_part}  kelly={kelly:g}"


def _scale_stakes(bets: list[dict], fraction: float) -> list[dict]:
    if abs(fraction - 1.0) < 1e-9:
        return bets
    out = []
    for b in bets:
        bb = dict(b)
        rs = bb.get("recommended_stake")
        if rs is not None:
            try:
                bb["recommended_stake"] = float(rs) * fraction
            except (TypeError, ValueError):
                pass
        out.append(bb)
    return out


# ── Core search ──────────────────────────────────────────────────────
def evaluate_strategy(
    bets: list[dict],
    sides, edge_lo, edge_hi, odds_lo, odds_hi, kelly,
    bankroll: float,
) -> Strategy | None:
    f = BetFilter(
        bet_sides=sides, min_edge=edge_lo, max_edge=edge_hi,
        min_odds=odds_lo, max_odds=odds_hi,
    )
    metrics = evaluate(bets, f)
    if metrics.total_bets == 0:
        return None
    selected = filter_bets(bets, f)
    selected = _scale_stakes(selected, kelly)
    bt = run_backtest(selected, initial_bankroll=bankroll).summary()

    growth_pct = bt.get("growth_pct", 0.0)
    max_dd_pct = bt.get("max_drawdown_pct", 0.0)
    score = _composite_score(metrics.roi * 100, growth_pct, max_dd_pct, metrics.total_bets)

    return Strategy(
        label=_label(sides, edge_lo, edge_hi, odds_lo, odds_hi, kelly),
        sides=sides, min_edge=edge_lo, max_edge=edge_hi,
        min_odds=odds_lo, max_odds=odds_hi, kelly_fraction=kelly,
        bets=metrics.total_bets,
        win_rate_pct=round(metrics.win_rate * 100, 2),
        roi_pct=round(metrics.roi * 100, 2),
        profit=round(metrics.profit, 4),
        avg_odds=round(metrics.avg_odds, 2),
        final_bankroll=round(bt["final_bankroll"], 4),
        growth_pct=round(growth_pct, 2),
        max_drawdown_pct=round(max_dd_pct, 2),
        score=score,
    )


def optimize(
    bets: list[dict],
    *,
    bankroll: float = START_BANKROLL,
    min_bets: int = 5,
    kelly_fractions: Iterable[float] = DEFAULT_KELLY_FRACTIONS,
    test_split: float = 0.0,
    score_metric: str = "composite",
) -> dict:
    """Run the full sweep and return ranked strategies with optional holdout test."""
    n = len(bets)
    if n == 0:
        return {"tested": 0, "kept": 0, "best": None, "rankings": []}

    if test_split and 0.0 < test_split < 1.0:
        cut = max(1, int(n * (1.0 - test_split)))
        train_bets, test_bets = bets[:cut], bets[cut:]
    else:
        train_bets, test_bets = bets, []

    rankings: list[Strategy] = []
    tested = 0
    for sides, (edge_lo, edge_hi), (odds_lo, odds_hi), kelly in product(
        SIDES, EDGE_BUCKETS, ODDS_BUCKETS, kelly_fractions,
    ):
        tested += 1
        s = evaluate_strategy(
            train_bets, sides, edge_lo, edge_hi, odds_lo, odds_hi, kelly, bankroll,
        )
        if s is None or s.bets < min_bets:
            continue
        rankings.append(s)

    sort_key = {
        "composite": lambda s: s.score,
        "roi":       lambda s: s.roi_pct,
        "growth":    lambda s: s.growth_pct,
        "profit":    lambda s: s.profit,
    }.get(score_metric, lambda s: s.score)
    rankings.sort(key=sort_key, reverse=True)

    # Out-of-sample test on the winner & top-N
    if test_bets:
        for s in rankings[:10]:
            t = evaluate_strategy(
                test_bets, s.sides, s.min_edge, s.max_edge,
                s.min_odds, s.max_odds, s.kelly_fraction, bankroll,
            )
            if t is not None:
                s.test_bets = t.bets
                s.test_roi_pct = t.roi_pct
                s.test_growth_pct = t.growth_pct
                s.test_max_drawdown_pct = t.max_drawdown_pct

    return {
        "n_dataset":   n,
        "n_train":     len(train_bets),
        "n_test":      len(test_bets),
        "tested":      tested,
        "kept":        len(rankings),
        "score_metric": score_metric,
        "best":        asdict(rankings[0]) if rankings else None,
        "rankings":    [asdict(s) for s in rankings],
    }


# ── CLI ──────────────────────────────────────────────────────────────
def _print_table(report: dict, top: int) -> None:
    print(f"\n=== Strategy Optimizer ===")
    print(f"  Dataset      : {report['n_dataset']} bets "
          f"(train={report['n_train']}, test={report['n_test']})")
    print(f"  Combinations : {report['tested']} tested, {report['kept']} met min-bets")
    print(f"  Score metric : {report['score_metric']}")
    if not report["best"]:
        print("\n  No strategies met the minimum bet count.")
        return

    has_test = report["n_test"] > 0
    hdr = f"  {'#':>2}  {'BETS':>5}  {'WR%':>6}  {'ROI%':>7}  {'GROW%':>7}  {'DD%':>5}  {'SCORE':>7}"
    if has_test:
        hdr += f"  {'tBETS':>5}  {'tROI%':>7}  {'tGROW%':>7}"
    hdr += "  STRATEGY"
    print(f"\n{hdr}")
    for i, s in enumerate(report["rankings"][:top], 1):
        row = (
            f"  {i:>2}  {s['bets']:>5}  {s['win_rate_pct']:>6.2f}  "
            f"{s['roi_pct']:>+7.2f}  {s['growth_pct']:>+7.2f}  "
            f"{s['max_drawdown_pct']:>5.2f}  {s['score']:>+7.4f}"
        )
        if has_test:
            tb = s.get("test_bets") or 0
            tr = s.get("test_roi_pct")
            tg = s.get("test_growth_pct")
            row += f"  {tb:>5}"
            row += f"  {tr:>+7.2f}" if tr is not None else f"  {'-':>7}"
            row += f"  {tg:>+7.2f}" if tg is not None else f"  {'-':>7}"
        row += f"  {s['label']}"
        print(row)

    print("\n  Best strategy:")
    b = report["best"]
    print(f"    {b['label']}")
    print(f"    bets={b['bets']}  ROI={b['roi_pct']:+.2f}%  "
          f"growth={b['growth_pct']:+.2f}%  max_dd={b['max_drawdown_pct']:.2f}%  "
          f"score={b['score']:+.4f}")
    if has_test and b.get("test_bets"):
        print(f"    out-of-sample: bets={b['test_bets']}  "
              f"ROI={b['test_roi_pct']:+.2f}%  growth={b['test_growth_pct']:+.2f}%")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Strategy optimizer with risk-adjusted scoring.")
    p.add_argument("dataset", nargs="?", help="Path to .csv or .json (omit for demo)")
    p.add_argument("--bankroll", type=float, default=START_BANKROLL)
    p.add_argument("--min-bets", type=int, default=5)
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--split", type=float, default=0.0,
                   help="Fraction of dataset held out for out-of-sample test (0 = none)")
    p.add_argument("--kelly", type=float, nargs="+", default=DEFAULT_KELLY_FRACTIONS,
                   help="Stake-fraction multipliers to sweep")
    p.add_argument("--score", choices=["composite", "roi", "growth", "profit"],
                   default="composite")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if args.dataset:
        path = Path(args.dataset)
        if not path.exists():
            print(f"error: not found: {path}", file=sys.stderr)
            return 2
        bets = _load(path)
    else:
        bets = _demo_dataset()

    report = optimize(
        bets,
        bankroll=args.bankroll,
        min_bets=args.min_bets,
        kelly_fractions=args.kelly,
        test_split=args.split,
        score_metric=args.score,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_table(report, args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
