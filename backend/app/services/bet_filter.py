"""Bet filtering & performance evaluation module.

Takes a dataset of bets (list of dicts or pandas DataFrame), applies filters on
bet side, edge thresholds, and odds range, and returns the selected bets along
with ROI and win-rate metrics.

Each bet record is expected to contain at minimum:
    - bet_side   : str   one of "home" | "draw" | "away" | "over_25" | "under_25" |
                          "btts_yes" | "btts_no" (case-insensitive; aliases handled)
    - odds       : float decimal odds (e.g. 2.10)
    - edge       : float model edge as fraction (0.05 = 5%) OR percent (5.0); both
                          accepted, see `edge_is_percent`
    - stake      : float stake placed (defaults to 1.0 unit if missing)
    - result     : str   "won" | "lost" | "void"  (case-insensitive)
                          OR a boolean `won` field; OR a numeric `pnl` field

The module never mutates the input dataset.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable, Optional, Sequence

try:                                # pandas is optional
    import pandas as pd
    _HAS_PANDAS = True
except Exception:                   # pragma: no cover
    pd = None                       # type: ignore
    _HAS_PANDAS = False


# ── Side normalisation ────────────────────────────────────────────────

_SIDE_ALIASES: dict[str, str] = {
    "1": "home", "h": "home", "home": "home",
    "x": "draw", "d": "draw", "draw": "draw",
    "2": "away", "a": "away", "away": "away",
    "over": "over_25", "over25": "over_25", "over_2.5": "over_25", "over_25": "over_25",
    "under": "under_25", "under25": "under_25", "under_2.5": "under_25", "under_25": "under_25",
    "btts": "btts_yes", "btts_yes": "btts_yes", "gg": "btts_yes",
    "btts_no": "btts_no", "ng": "btts_no",
}


def _normalise_side(side: Any) -> str:
    if side is None:
        return ""
    return _SIDE_ALIASES.get(str(side).strip().lower().replace(" ", "_"), str(side).lower())


# ── Filter & result containers ────────────────────────────────────────

@dataclass
class BetFilter:
    """Filter criteria applied to a dataset of bets."""
    bet_sides: Optional[Sequence[str]] = None      # e.g. ["home", "over_25"]; None = all
    min_edge: Optional[float] = None               # inclusive lower bound (fraction)
    max_edge: Optional[float] = None               # inclusive upper bound
    min_odds: Optional[float] = None
    max_odds: Optional[float] = None
    edge_is_percent: bool = False                  # if True, treat min/max_edge as %

    def normalised(self) -> "BetFilter":
        """Return a copy with side aliases resolved & edge bounds in fraction form."""
        sides = (
            [_normalise_side(s) for s in self.bet_sides]
            if self.bet_sides else None
        )
        scale = 100.0 if self.edge_is_percent else 1.0
        return BetFilter(
            bet_sides=sides,
            min_edge=(self.min_edge / scale) if self.min_edge is not None else None,
            max_edge=(self.max_edge / scale) if self.max_edge is not None else None,
            min_odds=self.min_odds,
            max_odds=self.max_odds,
            edge_is_percent=False,
        )


@dataclass
class FilterResult:
    bets: list[dict]                 = field(default_factory=list)
    total_bets: int                  = 0
    wins: int                        = 0
    losses: int                      = 0
    voids: int                       = 0
    total_staked: float              = 0.0
    total_returned: float            = 0.0    # gross returns from won bets (stake * odds)
    profit: float                    = 0.0    # total_returned - total_staked (excl. voids)
    roi: float                       = 0.0    # profit / total_staked      (fraction)
    win_rate: float                  = 0.0    # wins / settled              (fraction)
    avg_odds: float                  = 0.0
    avg_edge: float                  = 0.0
    yield_per_bet: float             = 0.0    # profit / total_bets         (fraction)
    filter_applied: dict             = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Internal helpers ──────────────────────────────────────────────────

def _coerce_records(dataset: Any) -> list[dict]:
    """Accept a list of dicts, a pandas DataFrame, or any iterable of mappings."""
    if dataset is None:
        return []
    if _HAS_PANDAS and isinstance(dataset, pd.DataFrame):
        return dataset.to_dict("records")
    if isinstance(dataset, dict):
        return [dataset]
    if isinstance(dataset, Iterable):
        return [dict(r) for r in dataset]
    raise TypeError(f"Unsupported dataset type: {type(dataset).__name__}")


def _resolve_result(bet: dict) -> str:
    """Return one of 'won' | 'lost' | 'void' | 'pending'."""
    r = bet.get("result")
    if r is not None:
        s = str(r).strip().lower()
        if s in ("won", "win", "w", "1", "true"):  return "won"
        if s in ("lost", "loss", "l", "0", "false"): return "lost"
        if s in ("void", "push", "refund", "cancelled", "canceled"): return "void"
        if s in ("pending", "open", "live"): return "pending"
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


def _passes(bet: dict, f: BetFilter) -> bool:
    if f.bet_sides:
        side = _normalise_side(bet.get("bet_side") or bet.get("side") or bet.get("prediction"))
        if side not in f.bet_sides:
            return False
    try:
        odds = float(bet.get("odds", 0) or 0)
    except (TypeError, ValueError):
        return False
    if f.min_odds is not None and odds < f.min_odds: return False
    if f.max_odds is not None and odds > f.max_odds: return False

    edge_raw = bet.get("edge")
    if edge_raw is None and "expected_value" in bet:
        edge_raw = bet["expected_value"]
    try:
        edge = float(edge_raw) if edge_raw is not None else None
    except (TypeError, ValueError):
        edge = None

    if f.min_edge is not None:
        if edge is None or edge < f.min_edge: return False
    if f.max_edge is not None:
        if edge is None or edge > f.max_edge: return False
    return True


# ── Public entry points ───────────────────────────────────────────────

def filter_bets(dataset: Any, filt: BetFilter) -> list[dict]:
    """Return only the bets in `dataset` that satisfy `filt`."""
    records = _coerce_records(dataset)
    f = filt.normalised()
    return [b for b in records if _passes(b, f)]


def evaluate(dataset: Any, filt: Optional[BetFilter] = None) -> FilterResult:
    """Filter (if `filt` given) and compute ROI / win-rate metrics."""
    f = (filt or BetFilter()).normalised()
    records = _coerce_records(dataset)
    selected = [b for b in records if _passes(b, f)]

    total_staked = 0.0
    total_returned = 0.0
    wins = losses = voids = 0
    odds_sum = 0.0
    edge_sum = 0.0
    edge_n = 0

    for b in selected:
        try:
            stake = float(b.get("stake", 1.0) or 1.0)
        except (TypeError, ValueError):
            stake = 1.0
        try:
            odds = float(b.get("odds", 0) or 0)
        except (TypeError, ValueError):
            odds = 0.0
        odds_sum += odds

        if b.get("edge") is not None:
            try:
                edge_sum += float(b["edge"]); edge_n += 1
            except (TypeError, ValueError):
                pass

        outcome = _resolve_result(b)
        if outcome == "won":
            wins += 1
            total_staked += stake
            total_returned += stake * odds
        elif outcome == "lost":
            losses += 1
            total_staked += stake
            # returned = 0
        elif outcome == "void":
            voids += 1
            total_staked += stake
            total_returned += stake          # stake refunded
        # pending bets are kept in `bets` but excluded from ROI math

    profit = total_returned - total_staked
    settled = wins + losses                  # voids excluded from win-rate denominator
    n = len(selected)

    return FilterResult(
        bets=selected,
        total_bets=n,
        wins=wins,
        losses=losses,
        voids=voids,
        total_staked=round(total_staked, 4),
        total_returned=round(total_returned, 4),
        profit=round(profit, 4),
        roi=round(profit / total_staked, 6) if total_staked > 0 else 0.0,
        win_rate=round(wins / settled, 6) if settled > 0 else 0.0,
        avg_odds=round(odds_sum / n, 4) if n > 0 else 0.0,
        avg_edge=round(edge_sum / edge_n, 6) if edge_n > 0 else 0.0,
        yield_per_bet=round(profit / n, 6) if n > 0 else 0.0,
        filter_applied={
            "bet_sides": list(f.bet_sides) if f.bet_sides else None,
            "min_edge": f.min_edge,
            "max_edge": f.max_edge,
            "min_odds": f.min_odds,
            "max_odds": f.max_odds,
        },
    )


__all__ = ["BetFilter", "FilterResult", "filter_bets", "evaluate"]
