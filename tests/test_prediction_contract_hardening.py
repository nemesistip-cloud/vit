from app.api.routes.predict import compute_model_consensus
from app.schemas.schemas import ModelInsight


def test_failed_model_insight_remains_serializable():
    insight = ModelInsight(
        model_name="unknown",
        model_type="algorithmic",
        model_weight=1.0,
        supported_markets=[],
        home_prob=None,
        draw_prob=None,
        away_prob=None,
        over_2_5_prob=None,
        btts_prob=None,
        home_goals_expectation=None,
        away_goals_expectation=None,
        confidence=0.0,
        latency_ms=1.0,
        failed=True,
        error="model failed",
    )

    assert insight.failed is True
    assert insight.model_name == "unknown"


def test_model_consensus_excludes_failed_models_from_votes():
    consensus = compute_model_consensus(
        [
            {"home_prob": 0.6, "draw_prob": 0.2, "away_prob": 0.2, "failed": False},
            {"failed": True},
        ],
        final_pick="home",
        total_specs=2,
    )

    assert consensus["votes"] == {"home": 1, "draw": 0, "away": 0}
    assert consensus["models_polled"] == 1