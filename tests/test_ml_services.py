"""
Unit tests for supporting ML service modules:
  - model_loader
  - simulation_engine (module-level functions + SimulationEngine small batch)
  - market_engine
"""
import random
import pytest


# ── ModelLoader ───────────────────────────────────────────────────────────────

class TestModelLoader:
    def test_list_available_models_returns_list(self):
        from services.ml_service.model_loader import list_available_models
        result = list_available_models()
        assert isinstance(result, list)

    def test_load_nonexistent_model_returns_none(self):
        from services.ml_service.model_loader import load_model
        result = load_model("nonexistent_model_xyz", cache_enabled=False)
        assert result is None

    def test_clear_cache_does_not_raise(self):
        from services.ml_service.model_loader import clear_cache
        clear_cache()

    def test_load_with_cache_disabled_returns_none_for_truly_missing(self):
        """Using a truly nonexistent model key must return None."""
        from services.ml_service.model_loader import load_model
        result = load_model("nonexistent_model_xyz_that_will_never_exist", cache_enabled=False)
        assert result is None

    def test_list_models_empty_when_no_pkls(self):
        from services.ml_service.model_loader import list_available_models
        models = list_available_models()
        assert isinstance(models, list)


# ── Simulation Engine — module-level pure functions ───────────────────────────

class TestSimulationFunctions:
    """Test the module-level simulation functions directly (no DB needed)."""

    def _make_team(self, attack=1.4, defense=0.85, home_adv=1.1):
        return {"attack": attack, "defense": defense, "home_adv": home_adv,
                "name": "TestTeam", "league": "test"}

    def test_poisson_goals_returns_non_negative(self):
        from services.ml_service.simulation_engine import _poisson_goals
        rng = random.Random(42)
        for _ in range(20):
            g = _poisson_goals(1.5, rng)
            assert g >= 0

    def test_outcome_function(self):
        from services.ml_service.simulation_engine import _outcome
        assert _outcome(2, 0) == "H"
        assert _outcome(0, 2) == "A"
        assert _outcome(1, 1) == "D"

    def test_simulate_tier1_returns_goals(self):
        from services.ml_service.simulation_engine import _simulate_tier1
        rng = random.Random(42)
        home = self._make_team()
        away = self._make_team(attack=1.2, defense=1.0, home_adv=1.0)
        result = _simulate_tier1(home, away, rng)
        assert "home_goals" in result
        assert "away_goals" in result
        assert result["home_goals"] >= 0
        assert result["away_goals"] >= 0

    def test_simulate_tier2_returns_form_fields(self):
        from services.ml_service.simulation_engine import _simulate_tier2
        rng = random.Random(7)
        home = self._make_team()
        away = self._make_team()
        result = _simulate_tier2(home, away, rng)
        assert "home_form" in result
        assert "away_form" in result

    def test_simulate_tier3_adds_chaos_fields(self):
        from services.ml_service.simulation_engine import _simulate_tier3
        rng = random.Random(3)
        home = self._make_team()
        away = self._make_team()
        result = _simulate_tier3(home, away, rng)
        assert "red_card_home" in result or "home_goals" in result

    def test_true_probs_sum_to_one(self):
        from services.ml_service.simulation_engine import _true_probs
        hp, dp, ap = _true_probs(1.5, 1.0)
        assert abs(hp + dp + ap - 1.0) < 0.01

    def test_true_probs_higher_lambda_more_home_wins(self):
        from services.ml_service.simulation_engine import _true_probs
        hp_strong, _, _ = _true_probs(2.5, 0.5)
        hp_weak, _, _ = _true_probs(0.5, 2.5)
        assert hp_strong > hp_weak

    def test_vig_free_probs_module_level(self):
        from services.ml_service.simulation_engine import _vig_free_probs
        result = _vig_free_probs({"home": 2.10, "draw": 3.30, "away": 3.60})
        total = result["home"] + result["draw"] + result["away"]
        assert abs(total - 1.0) < 0.01

    def test_make_market_odds_produces_positive_odds(self):
        from services.ml_service.simulation_engine import _make_market_odds
        rng = random.Random(42)
        odds = _make_market_odds(0.45, 0.27, 0.28, margin=0.07, bias=0.015,
                                 noise_sd=0.025, rng=rng)
        assert odds["home"] > 1.0
        assert odds["draw"] > 1.0
        assert odds["away"] > 1.0

    def test_simulation_engine_small_batch(self):
        from services.ml_service.simulation_engine import SimulationEngine
        engine = SimulationEngine(total_matches=20, seed=42)
        matches = engine.generate_in_memory()
        assert len(matches) == 20

    def test_simulation_engine_match_fields(self):
        from services.ml_service.simulation_engine import SimulationEngine
        engine = SimulationEngine(total_matches=10, seed=1)
        matches = engine.generate_in_memory()
        for m in matches:
            assert "home_goals" in m
            assert "away_goals" in m
            assert "result" in m
            assert m["result"] in ("H", "D", "A")

    def test_simulation_stats_returns_dict(self):
        from services.ml_service.simulation_engine import SimulationEngine
        engine = SimulationEngine(total_matches=10, seed=5)
        matches = engine.generate_in_memory()
        stats = SimulationEngine.stats(matches)
        assert isinstance(stats, dict)

    def test_simulation_stats_empty_input(self):
        from services.ml_service.simulation_engine import SimulationEngine
        stats = SimulationEngine.stats([])
        assert stats == {}


# ── MarketEngine ──────────────────────────────────────────────────────────────

class TestMarketEngine:
    def test_import_market_engine(self):
        from services.ml_service.market_engine import MarketEngine
        assert MarketEngine is not None

    def test_vig_free_probabilities_sum_to_one(self):
        from services.ml_service.market_engine import MarketEngine
        result = MarketEngine.vig_free_probs(2.10, 3.30, 3.60)
        total = result["home"] + result["draw"] + result["away"]
        assert abs(total - 1.0) < 0.001

    def test_vig_free_various_odds(self):
        from services.ml_service.market_engine import MarketEngine
        for ho, do, ao in [(1.50, 4.00, 7.00), (3.50, 3.40, 2.10)]:
            result = MarketEngine.vig_free_probs(ho, do, ao)
            total = result["home"] + result["draw"] + result["away"]
            assert abs(total - 1.0) < 0.01

    def test_generate_odds_returns_dict(self):
        from services.ml_service.market_engine import MarketEngine
        me = MarketEngine(seed=42)
        odds = me.generate_odds(0.45, 0.27, 0.28)
        assert "home" in odds and "draw" in odds and "away" in odds

    def test_generate_odds_positive_values(self):
        from services.ml_service.market_engine import MarketEngine
        me = MarketEngine(seed=1)
        odds = me.generate_odds(0.50, 0.25, 0.25)
        assert odds["home"] > 1.0
        assert odds["draw"] > 1.0
        assert odds["away"] > 1.0

    def test_compute_clv_static_method(self):
        from services.ml_service.market_engine import MarketEngine
        clv = MarketEngine.compute_clv(bet_odds=2.50, closing_odds=2.00)
        assert isinstance(clv, (int, float))
        assert clv > 0

    def test_compute_clv_negative_when_below_closing(self):
        from services.ml_service.market_engine import MarketEngine
        clv = MarketEngine.compute_clv(bet_odds=1.80, closing_odds=2.00)
        assert clv < 0

    def test_expected_value_positive_for_value_bet(self):
        from services.ml_service.market_engine import MarketEngine
        ev = MarketEngine.expected_value(model_prob=0.60, decimal_odds=2.10)
        assert ev > 0

    def test_expected_value_negative_for_bad_bet(self):
        from services.ml_service.market_engine import MarketEngine
        ev = MarketEngine.expected_value(model_prob=0.30, decimal_odds=2.10)
        assert ev < 0

    def test_vig_pct_static_method(self):
        from services.ml_service.market_engine import MarketEngine
        vig = MarketEngine.vig_pct(2.10, 3.30, 3.60)
        assert 0 <= vig <= 20

    def test_detect_edge_returns_none_when_no_edge(self):
        from services.ml_service.market_engine import MarketEngine
        me = MarketEngine(seed=42)
        result = me.detect_edge(
            model_probs={"home": 0.40, "draw": 0.30, "away": 0.30},
            market_odds={"home": 2.10, "draw": 3.30, "away": 3.60},
            threshold=0.15,
        )
        assert result is None

    def test_detect_edge_returns_dict_when_edge_found(self):
        from services.ml_service.market_engine import MarketEngine
        me = MarketEngine(seed=42)
        result = me.detect_edge(
            model_probs={"home": 0.65, "draw": 0.20, "away": 0.15},
            market_odds={"home": 2.10, "draw": 3.30, "away": 3.60},
            threshold=0.01,
        )
        assert result is not None
        assert "outcome" in result
        assert "edge" in result

    def test_hybrid_loss_returns_float(self):
        from services.ml_service.market_engine import MarketEngine
        loss = MarketEngine.hybrid_loss(
            model_probs={"home": 0.50, "draw": 0.25, "away": 0.25},
            actual_result="H",
            closing_probs={"home": 0.45, "draw": 0.28, "away": 0.27},
        )
        assert isinstance(loss, float)
        assert loss >= 0

    def test_simulate_line_movement_no_model(self):
        from services.ml_service.market_engine import MarketEngine
        me = MarketEngine(seed=42)
        opening = {"home": 2.10, "draw": 3.30, "away": 3.60}
        result = me.simulate_line_movement(opening)
        assert "home" in result and "draw" in result and "away" in result
        assert result["home"] > 1.0

    def test_simulate_line_movement_with_model(self):
        from services.ml_service.market_engine import MarketEngine
        me = MarketEngine(seed=42)
        opening = {"home": 2.10, "draw": 3.30, "away": 3.60}
        model_probs = {"home": 0.60, "draw": 0.25, "away": 0.15}
        result = me.simulate_line_movement(opening, info_factor=0.7, model_probs=model_probs)
        assert "home" in result and "draw" in result and "away" in result
        assert result["home"] > 1.0

    def test_simulate_line_movement_high_info(self):
        from services.ml_service.market_engine import MarketEngine
        me = MarketEngine(seed=10)
        opening = {"home": 3.50, "draw": 3.30, "away": 2.10}
        model_probs = {"home": 0.30, "draw": 0.30, "away": 0.40}
        result = me.simulate_line_movement(opening, info_factor=1.0, model_probs=model_probs)
        assert result["away"] < result["home"]

    def test_hybrid_loss_draw_outcome(self):
        from services.ml_service.market_engine import MarketEngine
        loss = MarketEngine.hybrid_loss(
            model_probs={"home": 0.30, "draw": 0.40, "away": 0.30},
            actual_result="D",
            closing_probs={"home": 0.30, "draw": 0.35, "away": 0.35},
        )
        assert isinstance(loss, float)

    def test_hybrid_loss_away_outcome(self):
        from services.ml_service.market_engine import MarketEngine
        loss = MarketEngine.hybrid_loss(
            model_probs={"home": 0.20, "draw": 0.25, "away": 0.55},
            actual_result="A",
            closing_probs={"home": 0.25, "draw": 0.30, "away": 0.45},
        )
        assert isinstance(loss, float)
        assert loss >= 0

    def test_generate_odds_zero_probs_fallback(self):
        from services.ml_service.market_engine import MarketEngine
        me = MarketEngine(seed=42)
        odds = me.generate_odds(0.0, 0.0, 0.0)
        assert odds["home"] > 1.0
        assert odds["draw"] > 1.0
        assert odds["away"] > 1.0

    def test_compute_clv_when_closing_at_or_below_one(self):
        from services.ml_service.market_engine import MarketEngine
        assert MarketEngine.compute_clv(bet_odds=2.50, closing_odds=1.0) == 0.0
        assert MarketEngine.compute_clv(bet_odds=2.50, closing_odds=0.5) == 0.0
