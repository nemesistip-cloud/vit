"""
Unit tests for the 13-model ML ensemble and supporting utilities.
These tests run entirely in Python — no HTTP or database calls.
"""
import math
import pytest
import os
from services.ml_service.models.model_orchestrator import ModelOrchestrator

@pytest.fixture(scope="module")
def orchestrator():
    # Force real models off to test algorithmic fallback
    os.environ["USE_REAL_ML_MODELS"] = "false"
    orch = ModelOrchestrator()
    return orch

def test_orchestrator_loads_13_models(orchestrator):
    assert len(orchestrator.models) == 13

def test_all_model_keys_present(orchestrator):
    expected = {
        "logistic_v2", "rf_v2", "xgb_v2", "poisson_v2", "elo_v2",
        "dixon_coles_v2", "lstm_v2", "transformer_v2", "ensemble_v2",
        "market_v2", "bayes_v2", "hybrid_v2", "llm_consensus_v1",
    }
    assert expected == set(orchestrator.models.keys())

def test_model_meta_has_required_fields(orchestrator):
    for key, meta in orchestrator.model_meta.items():
        assert "model_name" in meta
        assert "weight" in meta
        assert "pkl_loaded" in meta

@pytest.mark.asyncio
async def test_predict_returns_required_keys(orchestrator):
    features = {
        "home_team": "Arsenal",
        "away_team": "Man City",
        "market_odds": {"home": 2.40, "draw": 3.40, "away": 3.00},
    }
    result = await orchestrator.predict(features, "test_match_001")
    assert "predictions" in result
    preds = result["predictions"]
    for k in ["home_prob", "draw_prob", "away_prob", "over_25_prob", "btts_prob"]:
        assert k in preds

@pytest.mark.asyncio
async def test_predict_probabilities_sum_to_one(orchestrator):
    features = {
        "home_team": "Liverpool",
        "away_team": "Everton",
        "market_odds": {"home": 1.50, "draw": 4.50, "away": 6.50},
    }
    result = await orchestrator.predict(features, "test_match_002")
    preds = result["predictions"]
    total = preds["home_prob"] + preds["draw_prob"] + preds["away_prob"]
    # Check if sum is 1.0 with a small tolerance
    assert abs(total - 1.0) < 0.001

@pytest.mark.asyncio
async def test_predict_all_13_models_run(orchestrator):
    features = {
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "market_odds": {"home": 2.10, "draw": 3.60, "away": 3.20},
    }
    result = await orchestrator.predict(features, "test_match_008")
    assert result["models_count"] == 13
    assert len(result["individual_results"]) == 13

@pytest.mark.asyncio
async def test_predict_uses_real_weights_when_enabled():
    os.environ["USE_REAL_ML_MODELS"] = "true"
    # Ensure ModelLoader can find models
    os.environ["MODELS_DIR"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))

    orch = ModelOrchestrator()
    n_pkl = sum(orch._pkl_loaded.values())
    # Should have at least some real models loaded if .pkl files are present
    assert n_pkl > 0
