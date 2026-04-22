"""
Unit tests for the 12-model ML ensemble and supporting utilities.
These tests run entirely in Python — no HTTP or database calls.
"""
import math
import pytest

from services.ml_service.models.model_orchestrator import ModelOrchestrator


@pytest.fixture(scope="module")
def orchestrator():
    return ModelOrchestrator()


def test_orchestrator_loads_12_models(orchestrator):
    assert len(orchestrator.models) == 12


def test_all_model_keys_present(orchestrator):
    expected = {
        "logistic_v1", "rf_v1", "xgb_v1", "poisson_v1", "elo_v1",
        "dixon_coles_v1", "lstm_v1", "transformer_v1", "ensemble_v1",
        "market_v1", "bayes_v1", "hybrid_v1",
    }
    assert expected == set(orchestrator.models.keys())


def test_model_meta_has_required_fields(orchestrator):
    for key, meta in orchestrator.model_meta.items():
        assert "model_name" in meta, f"{key} missing model_name"
        assert "weight" in meta, f"{key} missing weight"
        assert "pkl_loaded" in meta, f"{key} missing pkl_loaded"


def _preds(result):
    """Extract the predictions sub-dict from an orchestrator result."""
    return result.get("predictions", result)


@pytest.mark.asyncio
async def test_predict_returns_required_keys(orchestrator):
    features = {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "market_odds": {"home": 2.10, "draw": 3.30, "away": 3.60},
    }
    result = await orchestrator.predict(features, "test_match_001")
    preds = _preds(result)
    required = {"home_prob", "draw_prob", "away_prob", "confidence",
                "over_25_prob", "under_25_prob", "btts_prob"}
    for key in required:
        assert key in preds, f"Missing key in predictions: {key}"


@pytest.mark.asyncio
async def test_predict_probabilities_sum_to_one(orchestrator):
    features = {
        "home_team": "Barcelona",
        "away_team": "RealMadrid",
        "market_odds": {"home": 2.50, "draw": 3.20, "away": 2.90},
    }
    result = await orchestrator.predict(features, "test_match_002")
    preds = _preds(result)
    total = preds["home_prob"] + preds["draw_prob"] + preds["away_prob"]
    assert abs(total - 1.0) < 0.02, f"Probs sum to {total}"


@pytest.mark.asyncio
async def test_predict_confidence_in_range(orchestrator):
    features = {
        "home_team": "ManCity",
        "away_team": "Liverpool",
        "market_odds": {"home": 1.80, "draw": 3.50, "away": 4.50},
    }
    result = await orchestrator.predict(features, "test_match_003")
    preds = _preds(result)
    conf = preds["confidence"]
    if isinstance(conf, dict):
        val = conf.get("1x2", 0)
    else:
        val = conf
    assert 0.0 <= val <= 1.0


@pytest.mark.asyncio
async def test_predict_over_under_sums_to_one(orchestrator):
    features = {
        "home_team": "Bayern",
        "away_team": "Dortmund",
        "market_odds": {"home": 1.60, "draw": 4.20, "away": 6.00},
    }
    result = await orchestrator.predict(features, "test_match_004")
    preds = _preds(result)
    total = preds["over_25_prob"] + preds["under_25_prob"]
    assert abs(total - 1.0) < 0.02, f"O/U sum: {total}"


@pytest.mark.asyncio
async def test_predict_includes_models_used(orchestrator):
    features = {
        "home_team": "PSG",
        "away_team": "Marseille",
        "market_odds": {"home": 1.40, "draw": 4.50, "away": 8.00},
    }
    result = await orchestrator.predict(features, "test_match_005")
    preds = _preds(result)
    assert "models_used" in preds
    assert preds["models_used"] == 12


@pytest.mark.asyncio
async def test_predict_with_missing_odds_uses_defaults(orchestrator):
    """Orchestrator should handle missing market_odds gracefully."""
    features = {
        "home_team": "Juventus",
        "away_team": "Milan",
    }
    result = await orchestrator.predict(features, "test_match_006")
    preds = _preds(result)
    assert "home_prob" in preds
    assert preds["home_prob"] + preds["draw_prob"] + preds["away_prob"] > 0.98


@pytest.mark.asyncio
async def test_predict_all_12_models_run(orchestrator):
    features = {
        "home_team": "Ajax",
        "away_team": "PSV",
        "market_odds": {"home": 1.95, "draw": 3.40, "away": 4.10},
    }
    result = await orchestrator.predict(features, "test_match_007")
    preds = _preds(result)
    assert preds.get("models_used") == 12


@pytest.mark.asyncio
async def test_predict_btts_in_range(orchestrator):
    features = {
        "home_team": "Leicester",
        "away_team": "Everton",
        "market_odds": {"home": 2.20, "draw": 3.10, "away": 3.40},
    }
    result = await orchestrator.predict(features, "test_match_008")
    preds = _preds(result)
    assert 0.0 <= preds["btts_prob"] <= 1.0


@pytest.mark.asyncio
async def test_predict_different_matches_give_different_results(orchestrator):
    feat_home_fav = {
        "home_team": "City",
        "away_team": "Burnley",
        "market_odds": {"home": 1.25, "draw": 6.00, "away": 12.0},
    }
    feat_away_fav = {
        "home_team": "Burnley",
        "away_team": "City",
        "market_odds": {"home": 9.00, "draw": 5.50, "away": 1.38},
    }
    r1 = await orchestrator.predict(feat_home_fav, "test_match_009a")
    r2 = await orchestrator.predict(feat_away_fav, "test_match_009b")
    p1 = _preds(r1)
    p2 = _preds(r2)
    assert p1["home_prob"] != p2["home_prob"]


@pytest.mark.asyncio
async def test_predict_includes_individual_results(orchestrator):
    features = {
        "home_team": "Porto",
        "away_team": "Benfica",
        "market_odds": {"home": 2.60, "draw": 3.20, "away": 2.80},
    }
    result = await orchestrator.predict(features, "test_match_010")
    assert "individual_results" in result
    assert len(result["individual_results"]) == 12


@pytest.mark.asyncio
async def test_predict_uses_algorithmic_fallback_when_no_pkl(orchestrator):
    """With USE_REAL_ML_MODELS=false, no pkl should be loaded."""
    for key, loaded in orchestrator._pkl_loaded.items():
        assert not loaded, f"{key} has pkl loaded but USE_REAL_ML_MODELS=false"
