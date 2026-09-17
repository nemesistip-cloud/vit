from services.ml_service.models.model_orchestrator import ModelOrchestrator


class _ProbabilityModel:
    key = "test-model"
    _sklearn_model = None
    _sklearn_features = ["home_odds", "draw_odds", "away_odds", "over_25_implied"]
    _sklearn_scaler = None

    def __init__(self):
        self.received = None
        self._sklearn_model = self

    def predict_proba(self, values):
        self.received = values
        return [[0.5, 0.3, 0.2]]


def test_sklearn_prediction_uses_numeric_over_under_feature():
    model = _ProbabilityModel()
    orchestrator = ModelOrchestrator.__new__(ModelOrchestrator)

    result = orchestrator._sklearn_predict(
        model,
        lam_h=1.4,
        lam_a=1.1,
        base_hp=0.45,
        base_dp=0.25,
        base_ap=0.30,
        market_odds={"home": 2.2, "draw": 3.4, "away": 3.2},
        match_features={},
    )

    assert result == (0.5, 0.3, 0.2)
    assert model.received[0][-1] == 0.5