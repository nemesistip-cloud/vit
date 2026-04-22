# app/training/quality_scorer.py — Module D2
# Data Quality Scorer: score_dataset() function
# Weights: Completeness 25%, Sample Size 20%, Recency 20%, Feature Coverage 20%, Variance 15%

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List


_REQUIRED_FEATURES = [
    "home_team", "away_team", "league", "home_goals", "away_goals"
]

_BONUS_FEATURES = [
    "market_odds", "kickoff_time", "season", "matchday",
    "vig_free_probs", "over_25", "btts", "total_goals",
    "home_xg", "away_xg", "home_shots", "away_shots",
]


def score_dataset(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Score a list of match records for training readiness.
    Returns a score 0-100 and a per-dimension breakdown.
    """
    if not records:
        return {
            "score": 0,
            "grade": "F",
            "breakdown": {},
            "issues": ["Dataset is empty"],
            "recommendations": ["Upload historical match data with at least 200 records"],
        }

    issues: List[str] = []
    recommendations: List[str] = []

    # ── Dimension 1: Completeness (25%) ────────────────────────────────
    required_present = 0
    for record in records:
        if all(field in record and record[field] is not None for field in _REQUIRED_FEATURES):
            required_present += 1

    completeness_rate = required_present / len(records)
    completeness_score = completeness_rate * 100

    if completeness_rate < 0.9:
        issues.append(f"Only {completeness_rate:.0%} of records have all required fields")
        recommendations.append("Ensure every record has: home_team, away_team, league, home_goals, away_goals")

    # ── Dimension 2: Sample Size (20%) ─────────────────────────────────
    n = len(records)
    if n >= 5000:
        sample_score = 100
    elif n >= 2000:
        sample_score = 80 + (n - 2000) / 3000 * 20
    elif n >= 500:
        sample_score = 50 + (n - 500) / 1500 * 30
    elif n >= 200:
        sample_score = 30 + (n - 200) / 300 * 20
    else:
        sample_score = (n / 200) * 30
        issues.append(f"Only {n} records — models need at least 200 to train meaningfully")
        recommendations.append("Aim for 2,000+ records for reliable model training")

    if n < 2000:
        recommendations.append(f"Current: {n} records. Target: 2,000+ for good accuracy, 5,000+ for excellent")

    # ── Dimension 3: Recency (20%) ─────────────────────────────────────
    recency_score = 0.0
    dates_found = 0
    now = datetime.now(timezone.utc)

    for record in records:
        date_val = record.get("kickoff_time") or record.get("date") or record.get("match_date")
        if date_val:
            try:
                if isinstance(date_val, str):
                    date_val = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                if isinstance(date_val, datetime):
                    if date_val.tzinfo is None:
                        date_val = date_val.replace(tzinfo=timezone.utc)
                    age_days = (now - date_val).days
                    if age_days <= 365:
                        recency_score += 100
                    elif age_days <= 730:
                        recency_score += 70
                    elif age_days <= 1825:
                        recency_score += 40
                    else:
                        recency_score += 10
                    dates_found += 1
            except Exception:
                continue

    if dates_found > 0:
        recency_score = recency_score / dates_found
    else:
        recency_score = 50
        recommendations.append("Add kickoff_time or date field to enable recency scoring")

    # ── Dimension 4: Feature Coverage (20%) ────────────────────────────
    bonus_counts = {feat: 0 for feat in _BONUS_FEATURES}
    for record in records:
        for feat in _BONUS_FEATURES:
            if feat in record and record[feat] is not None:
                bonus_counts[feat] += 1

    coverage_rates = [bonus_counts[f] / n for f in _BONUS_FEATURES]
    feature_coverage_score = (sum(coverage_rates) / len(_BONUS_FEATURES)) * 100

    missing_high_value = [
        f for f in ["market_odds", "kickoff_time", "over_25"]
        if bonus_counts[f] / n < 0.5
    ]
    if missing_high_value:
        issues.append(f"Missing high-value features: {', '.join(missing_high_value)}")
        recommendations.append(f"Add {', '.join(missing_high_value)} to improve model accuracy significantly")

    # ── Dimension 5: Variance (15%) ────────────────────────────────────
    outcomes = {"home": 0, "draw": 0, "away": 0}
    for record in records:
        hg = record.get("home_goals")
        ag = record.get("away_goals")
        if hg is not None and ag is not None:
            try:
                hg, ag = int(hg), int(ag)
                if hg > ag:
                    outcomes["home"] += 1
                elif hg == ag:
                    outcomes["draw"] += 1
                else:
                    outcomes["away"] += 1
            except (ValueError, TypeError):
                continue

    total_outcomes = sum(outcomes.values())
    if total_outcomes > 0:
        probs = [v / total_outcomes for v in outcomes.values()]
        entropy = -sum(p * math.log(p + 1e-9) for p in probs if p > 0)
        max_entropy = math.log(3)
        variance_score = (entropy / max_entropy) * 100

        dominant = max(probs)
        if dominant > 0.65:
            dominant_label = max(outcomes, key=outcomes.get)
            issues.append(f"Dataset skewed — {dominant_label} wins are {dominant:.0%} of records")
            recommendations.append("Balance dataset across home wins, draws, and away wins for unbiased training")
    else:
        variance_score = 50

    # ── Composite Score ────────────────────────────────────────────────
    score = (
        completeness_score * 0.25 +
        sample_score * 0.20 +
        recency_score * 0.20 +
        feature_coverage_score * 0.20 +
        variance_score * 0.15
    )
    score = round(score, 1)

    if score >= 85:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 55:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "record_count": n,
        "breakdown": {
            "completeness": round(completeness_score, 1),
            "sample_size": round(sample_score, 1),
            "recency": round(recency_score, 1),
            "feature_coverage": round(feature_coverage_score, 1),
            "variance": round(variance_score, 1),
        },
        "feature_coverage_detail": {
            feat: f"{bonus_counts[feat] / n:.0%}" for feat in _BONUS_FEATURES
        },
        "outcome_distribution": outcomes,
        "issues": issues,
        "recommendations": recommendations,
    }
