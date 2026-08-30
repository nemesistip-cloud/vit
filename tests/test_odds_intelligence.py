"""
Unit and integration tests for Odds Intelligence Layer, Provider Registry,
Evidence Engine, and Prediction Availability.
"""

import pytest
from datetime import datetime, timezone
from app.services.odds_provider import (
    NormalizedOdds,
    OddsIntelligence,
    OddsFreshness,
    ProviderRegistry,
    OddsAPIProviderAdapter,
    ISportsProviderAdapter,
    FootballDataProviderAdapter,
    SportsDBProviderAdapter,
)
from app.services.evidence_engine import (
    EvidenceEngine,
    PredictionClassification,
    MARKET_REQUIREMENTS,
)


def test_odds_normalization_and_freshness():
    now = datetime.now(timezone.utc)
    odds_live = NormalizedOdds(
        fixture_id="fix_101",
        sport="football",
        market="match_winner",
        selection="home",
        odds=2.10,
        bookmaker="BetWay",
        timestamp=now,
        provider="odds_api",
    )
    assert odds_live.freshness == OddsFreshness.LIVE
    assert odds_live.age_seconds < 5.0


def test_odds_reconciliation_and_anomaly_detection():
    now = datetime.now(timezone.utc)
    # Normal odds set
    odds_a = [
        NormalizedOdds("fix_1", "football", "match_winner", "home", 2.10, "BM1", now, "p1"),
        NormalizedOdds("fix_1", "football", "match_winner", "draw", 3.25, "BM1", now, "p1"),
        NormalizedOdds("fix_1", "football", "match_winner", "away", 3.60, "BM1", now, "p1"),
        NormalizedOdds("fix_1", "football", "match_winner", "home", 2.05, "BM2", now, "p2"),
        NormalizedOdds("fix_1", "football", "match_winner", "draw", 3.30, "BM2", now, "p2"),
        NormalizedOdds("fix_1", "football", "match_winner", "away", 3.50, "BM2", now, "p2"),
    ]
    reconciled = OddsIntelligence.reconcile(odds_a, sport="football", market="match_winner")
    assert reconciled is not None
    assert reconciled.bookmaker_count == 2
    assert reconciled.has_anomaly is False
    assert 2.0 <= reconciled.consensus_odds["home"] <= 2.15
    assert reconciled.margin > 0.0
    assert sum(reconciled.vig_free_probabilities.values()) == pytest.approx(1.0, abs=1e-3)

    # Anomaly odds set (Home odds vary widely: 1.50 vs 2.80 -> ratio > 1.35)
    odds_anomaly = [
        NormalizedOdds("fix_2", "football", "match_winner", "home", 1.50, "BM1", now, "p1"),
        NormalizedOdds("fix_2", "football", "match_winner", "draw", 3.25, "BM1", now, "p1"),
        NormalizedOdds("fix_2", "football", "match_winner", "away", 3.60, "BM1", now, "p1"),
        NormalizedOdds("fix_2", "football", "match_winner", "home", 2.80, "BM2", now, "p2"),
        NormalizedOdds("fix_2", "football", "match_winner", "draw", 3.30, "BM2", now, "p2"),
        NormalizedOdds("fix_2", "football", "match_winner", "away", 3.50, "BM2", now, "p2"),
    ]
    reconciled_anom = OddsIntelligence.reconcile(odds_anomaly, sport="football", market="match_winner")
    assert reconciled_anom is not None
    assert reconciled_anom.has_anomaly is True
    assert "ODDS_ANOMALY" in reconciled_anom.anomaly_reason


def test_evidence_engine_evaluation_scores():
    now = datetime.now(timezone.utc)

    # High evidence match
    odds = OddsIntelligence.reconcile([
        NormalizedOdds("f1", "football", "match_winner", "home", 2.10, "BM1", now, "p1"),
        NormalizedOdds("f1", "football", "match_winner", "draw", 3.25, "BM1", now, "p1"),
        NormalizedOdds("f1", "football", "match_winner", "away", 3.60, "BM1", now, "p1"),
    ])

    breakdown_strong = EvidenceEngine.evaluate(
        match_source="isports",
        match_features={"feature_completeness": 1.0},
        reconciled_odds=odds,
        h2h_data={"matches_played": 5},
        recent_form_data={"home": {"matches_played": 5}, "away": {"matches_played": 5}},
        model_agreement_pct=0.9,
    )
    assert breakdown_strong.total_score >= 85.0
    assert breakdown_strong.classification == PredictionClassification.STRONG
    assert breakdown_strong.is_sufficient is True

    # Low evidence match (Unverified source, missing features)
    breakdown_unavail = EvidenceEngine.evaluate(
        match_source="unverified_source",
        match_features={"feature_completeness": 0.0},
    )
    assert breakdown_unavail.total_score < 55.0
    assert breakdown_unavail.classification == PredictionClassification.UNAVAILABLE
    assert breakdown_unavail.is_sufficient is False
    assert len(breakdown_unavail.missing_elements) > 0


def test_market_specific_input_requirements():
    # over_2_5 requires current_market_odds
    breakdown_no_odds = EvidenceEngine.evaluate(
        match_source="isports",
        match_features={"feature_completeness": 1.0},
        reconciled_odds=None,
        market="over_2_5"
    )
    assert breakdown_no_odds.is_sufficient is False
    assert breakdown_no_odds.classification == PredictionClassification.UNAVAILABLE
    assert "strictly requires market odds" in (breakdown_no_odds.rejection_reason or "")


@pytest.mark.asyncio
async def test_provider_registry_health_matrix():
    registry = ProviderRegistry()
    registry.register_odds_provider("odds_api", OddsAPIProviderAdapter())
    registry.register_odds_provider("isports", ISportsProviderAdapter())

    matrix = await registry.get_health_matrix()
    assert isinstance(matrix, list)
    assert len(matrix) >= 5

    football = next(item for item in matrix if item["sport"] == "Football")
    assert football["status"] == "Ready"
    assert football["active_odds_providers"] == 2
