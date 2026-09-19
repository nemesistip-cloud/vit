from app.services.match_intelligence import MatchIntelligenceProfile, PredictionReadinessGate, ValidationStatus


def test_match_intelligence_profile_tracks_validation_and_missing_data():
    profile = MatchIntelligenceProfile(
        fixture_id="560587",
        home_team="Tottenham Hotspur FC",
        away_team="Aston Villa FC",
        competition="Premier League",
        season="2025/26",
        feature_completeness=0.82,
        data_quality_score=81.0,
        validation_status=ValidationStatus.VALID,
    )

    profile.mark_missing("Current market odds")
    profile.mark_conflict("Odds disagreement across bookmakers")

    assert profile.fixture_id == "560587"
    assert profile.validation_status == ValidationStatus.VALID
    assert "Current market odds" in profile.missing_data_reasons
    assert "Odds disagreement across bookmakers" in profile.conflicting_reasons


def test_prediction_readiness_gate_blocks_insufficient_evidence():
    gate = PredictionReadinessGate(
        min_feature_completeness=0.8,
        min_evidence_score=55.0,
        min_history_samples=3,
    )

    result = gate.evaluate(
        feature_completeness=0.5,
        evidence_score=27.7,
        odds_available=False,
        historical_sample_size=2,
        data_freshness_ok=False,
        model_ready=True,
    )

    assert result["prediction_status"] == "unavailable"
    assert result["ready"] is False
    assert any("feature completeness" in reason.lower() for reason in result["reasons"])
    assert any("evidence score" in reason.lower() for reason in result["reasons"])


def test_prediction_readiness_gate_allows_valid_match():
    gate = PredictionReadinessGate(
        min_feature_completeness=0.8,
        min_evidence_score=55.0,
        min_history_samples=3,
    )

    result = gate.evaluate(
        feature_completeness=0.86,
        evidence_score=81.0,
        odds_available=True,
        historical_sample_size=8,
        data_freshness_ok=True,
        model_ready=True,
    )

    assert result["prediction_status"] == "ready"
    assert result["ready"] is True
    assert result["reasons"] == []
