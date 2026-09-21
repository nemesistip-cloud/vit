"""Data Quality Scorer — Module D2.

Wraps the existing quality_scorer with the Module D interface.
score_dataset(df, league, date_from, date_to) → quality_score, breakdown
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.training.quality_scorer import score_dataset as _score_records


def score_dataset(
    df: List[Dict[str, Any]],
    league: str = "unknown",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Score a list of match record dicts.

    Parameters
    ----------
    df          : list of dicts — each dict is one match record
    league      : league name (informational)
    date_from   : start of date range (informational)
    date_to     : end of date range (informational)

    Returns
    -------
    dict with keys:
        quality_score   : float 0-100
        grade           : str (A/B/C/D/F)
        breakdown       : dict of per-dimension scores
        issues          : list of str
        recommendations : list of str
        record_count    : int
        feature_coverage_detail : dict
        outcome_distribution    : dict
    """
    report = _score_records(df)

    report["league"] = league
    report["date_from"] = str(date_from) if date_from else None
    report["date_to"] = str(date_to) if date_to else None

    return report


def build_column_profile(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarise which columns are present and their coverage rates."""
    if not records:
        return {}

    all_keys = set()
    for r in records:
        all_keys.update(r.keys())

    profile: Dict[str, Any] = {}
    n = len(records)
    for key in sorted(all_keys):
        filled = sum(1 for r in records if r.get(key) is not None)
        profile[key] = {
            "coverage": round(filled / n, 4),
            "filled": filled,
            "missing": n - filled,
        }
    return profile
