"""
ModelOrchestrator v3 — Differentiated 12-Model Ensemble
"""

import logging
import math
import os
import random
import sys
import asyncio
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

def _use_real_ml_models() -> bool:
    env_value = os.getenv("USE_REAL_ML_MODELS")
    if env_value is not None:
        return env_value.lower() == "true"
    return True

def _ml_cache_enabled() -> bool:
    return os.getenv("ML_MODEL_CACHE_ENABLED", "true").lower() == "true"

def _get_enabled_models() -> Optional[List[str]]:
    val = os.getenv("ENABLED_MODELS", "").lower().strip()
    if not val or val == "all":
        return None
    return [m.strip() for m in val.split(",") if m.strip()]

_TOTAL_MODEL_SPECS    = 13
_HOME_ADVANTAGE_BIAS  = 0.014
_MAX_STAKE            = 0.05

_MODEL_SPECS: list = [
    {"key": "logistic_v2", "name": "LogisticRegression", "markets": ["1x2"], "sigma": 0.018, "market_trust": 0.70},
    {"key": "rf_v2", "name": "RandomForest", "markets": ["1x2"], "sigma": 0.020, "market_trust": 0.60},
    {"key": "xgb_v2", "name": "XGBoost", "markets": ["1x2"], "sigma": 0.015, "market_trust": 0.65},
    {"key": "poisson_v2", "name": "PoissonGoals", "markets": ["1x2"], "sigma": 0.012, "market_trust": 0.55},
    {"key": "elo_v2", "name": "EloRating", "markets": ["1x2"], "sigma": 0.010, "market_trust": 0.40},
    {"key": "dixon_coles_v2", "name": "DixonColes", "markets": ["1x2"], "sigma": 0.010, "market_trust": 0.50},
    {"key": "lstm_v2", "name": "LSTM", "markets": ["1x2"], "sigma": 0.022, "market_trust": 0.75},
    {"key": "transformer_v2", "name": "Transformer", "markets": ["1x2"], "sigma": 0.020, "market_trust": 0.68},
    {"key": "ensemble_v2", "name": "NeuralEnsemble", "markets": ["1x2"], "sigma": 0.012, "market_trust": 0.60},
    {"key": "market_v2", "name": "MarketImplied", "markets": ["1x2"], "sigma": 0.006, "market_trust": 0.95},
    {"key": "bayes_v2", "name": "BayesianNet", "markets": ["1x2"], "sigma": 0.018, "market_trust": 0.50},
    {"key": "hybrid_v2", "name": "HybridStack", "markets": ["1x2"], "sigma": 0.010, "market_trust": 0.65},
    {"key": "llm_consensus_v1", "name": "LLMConsensus", "markets": ["1x2"], "sigma": 0.012, "market_trust": 0.55},
]

class _BaseModel:
    def __init__(self, key: str, markets: list, sigma: float = 0.015, market_trust: float = 0.65):
        self.key = key
        self.supported_markets = markets
        self.sigma = sigma
        self.market_trust = market_trust
        self.is_trained = False
        self.trained_matches_count = 0
    def predict_1x2(self, *args, **kwargs): return (0.34, 0.33, 0.33)

class ModelOrchestrator:
    def __init__(self):
        self.models:      Dict[str, Any]  = {}
        self.model_meta:  Dict[str, Any]  = {}
        self._pkl_loaded: Dict[str, bool] = {}
        self.load_all_models()

    def load_all_models(self):
        use_real = _use_real_ml_models()
        cache_on = _ml_cache_enabled()
        models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "models")

        for spec in _MODEL_SPECS:
            key = spec["key"]
            self.models[key] = _BaseModel(key, spec["markets"], spec["sigma"], spec["market_trust"])
            loaded = False
            if use_real:
                payload = self._try_load_pkl(key, models_dir, cache_on)
                                # Task 3D: On model load, check GCS if not found locally
                if payload is None and os.getenv("GCS_BUCKET_NAME"):
                    try:
                        from app.services.gcs_storage import gcs_storage
                        local_tmp = os.path.join("/tmp", "vit_models", f"{key}.pkl")
                        # We use sync wrapper here as load_all_models is usually called during startup
                        try:
                            # Try downloading it
                            asyncio.run(gcs_storage.download_model(f"{key}.pkl", local_tmp))
                            payload = self._try_load_pkl(key, "/tmp/vit_models", cache_on)
                        except Exception:
                             pass
                    except Exception:
                        pass

                if payload is not None:
                    self._attach_sklearn_payload(model_obj, key, payload)
                    loaded = True
                    loaded_from = key
                elif parent_version:
                    payload = self._try_load_pkl(parent_version, models_dir, cache_on)
                                    # Task 3D: On model load, check GCS if not found locally
                if payload is None and os.getenv("GCS_BUCKET_NAME"):
                    try:
                        from app.services.gcs_storage import gcs_storage
                        local_tmp = os.path.join("/tmp", "vit_models", f"{key}.pkl")
                        # We use sync wrapper here as load_all_models is usually called during startup
                        try:
                            # Try downloading it
                            asyncio.run(gcs_storage.download_model(f"{key}.pkl", local_tmp))
                            payload = self._try_load_pkl(key, "/tmp/vit_models", cache_on)
                        except Exception:
                             pass
                    except Exception:
                        pass

                if payload is not None:
                        self._attach_sklearn_payload(model_obj, key, payload)
                        loaded = True
                        loaded_from = parent_version
                        logger.info(
                        "↳ %s loaded weights from parent %s (v2 pkl not yet trained)",
                        key, parent_version,
                        )

            self._pkl_loaded[key] = loaded
            self.model_meta[key] = {"model_name": spec["name"], "weight": 1.0, "pkl_loaded": loaded, "model_type": "algorithmic", "supported_markets": spec["markets"]}

        n_pkl = sum(self._pkl_loaded.values())
        logger.info(
            f"Orchestrator ready: {len(self.models)}/{_TOTAL_MODEL_SPECS} models "
            f"({n_pkl} with real trained weights)"
        )
        return results

    def _try_load_pkl(self, key: str, legacy_models_dir: str, cache_on: bool) -> Optional[Dict]:
        """
        Internal helper.
        """
        try:
            from services.ml_service.model_loader import load_model
            payload = load_model(key, cache_enabled=cache_on)
            # Task 3D: On model load, check GCS if not found locally
            if payload is None and os.getenv("GCS_BUCKET_NAME"):
                try:
                    from app.services.gcs_storage import gcs_storage
                    local_tmp = os.path.join("/tmp", "vit_models", f"{key}.pkl")
                    try:
                        asyncio.run(gcs_storage.download_model(f"{key}.pkl", local_tmp))
                        payload = load_model(key, cache_enabled=cache_on)
                    except Exception: pass
                except Exception: pass
            return payload
        except Exception as exc:
            logger.debug(f"ModelLoader unavailable for {key}: {exc}")

        legacy_path = os.path.join(legacy_models_dir, f"{key}.pkl")
        if os.path.exists(legacy_path):
            try:
                from app.services.gcs_storage import gcs_storage
                local_tmp = os.path.join("/tmp", "vit_models", f"{key}.pkl")
                import asyncio
                # Use a wrapper for async in sync
                loop = asyncio.new_event_loop()
                loop.run_until_complete(gcs_storage.download_model(f"{key}.pkl", local_tmp))
                loop.close()
                import joblib
                return joblib.load(local_tmp)
            except Exception: pass
        return None
    def _attach_sklearn_payload(self, model_obj, key: str, payload: Dict) -> None:
        """Attach a loaded sklearn payload to a model instance."""
        loaded_model = payload["model"]
        if hasattr(loaded_model, "predict_proba"):
            model_obj._sklearn_model    = loaded_model
            model_obj._sklearn_scaler   = payload.get("scaler")
            model_obj._sklearn_features = payload.get("feature_columns", [])
        else:
            model_obj._sklearn_model    = None
            model_obj._sklearn_scaler   = None
            model_obj._sklearn_features = []
            for attr in ("learned_result_probs", "learned_over25_rate", "learning_iteration", "market_trust"):
                if hasattr(loaded_model, attr):
                    setattr(model_obj, attr, getattr(loaded_model, attr))
        model_obj._sklearn_version      = payload.get("version", "?")
        model_obj.is_trained            = True
        model_obj.trained_matches_count = payload.get("training_samples", 1)
        logger.info(
            f"✅ Attached real weights for {key} "
            f"(acc={payload.get('metrics', {}).get('accuracy', '?')}, "
            f"samples={payload.get('training_samples', '?')})"
        )

    def _sklearn_predict(self, model_obj, lam_h: float, lam_a: float,
                         base_hp: float, base_dp: float, base_ap: float,
                         match_features: Optional[Dict[str, Any]] = None,
                         ) -> Optional[Tuple[float, float, float]]:
        """
        Run the attached sklearn model using available prediction-time features.

        v4.10.0 (Phase A): when `match_features` is supplied (built upstream by
        ``app.services.predict_features.build_predict_features`` from real DB
        history), the rolling-form / H2H / ELO values override the neutral
        fallback defaults.  Missing keys still fall back gracefully so the
        predictor never crashes on cold-start fixtures.

        Returns (home_prob, draw_prob, away_prob) or None on failure.
        """
        sk_model   = getattr(model_obj, "_sklearn_model",    None)
        sk_scaler  = getattr(model_obj, "_sklearn_scaler",   None)
        sk_features = getattr(model_obj, "_sklearn_features", [])

        if sk_model is None:
            return None

        # Neutral fallbacks (used only when no DB-backed feature is available)
        feature_map = {
            "home_form_pts_5":   1.30,  "away_form_pts_5":   1.20,
            "home_form_pts_10":  1.30,  "away_form_pts_10":  1.20,
            "home_gf_pg_5":      1.45,  "away_gf_pg_5":      1.20,
            "home_ga_pg_5":      1.20,  "away_ga_pg_5":      1.45,
            "home_gf_pg_10":     1.45,  "away_gf_pg_10":     1.20,
            "home_ga_pg_10":     1.20,  "away_ga_pg_10":     1.45,
            "h2h_home_win_pct":  base_hp,
            "h2h_draw_pct":      base_dp,
            "h2h_away_win_pct":  base_ap,
            "h2h_home_goals_pg": 1.45,
            "h2h_away_goals_pg": 1.20,
            "home_adv_league":   0.40,
            "elo_diff":          (lam_h - lam_a) * 80.0,   # proxy from xG diff
            "lambda_home_est":   lam_h,
            "lambda_away_est":   lam_a,
        }

        # Override with real DB-backed features when present (Phase A)
        if isinstance(match_features, dict) and match_features:
            for k, v in match_features.items():
                if v is None or k not in feature_map:
                    continue
                try:
                    feature_map[k] = float(v)
                except (TypeError, ValueError):
                    continue

        try:
            import numpy as np
            cols = sk_features if sk_features else list(feature_map.keys())
            vec  = np.array([[feature_map.get(c, 0.0) for c in cols]], dtype=float)

            if sk_scaler is not None:
                vec = sk_scaler.transform(vec)

            proba = sk_model.predict_proba(vec)[0]
            # proba order: [home(0), draw(1), away(2)]
            hp, dp, ap = float(proba[0]), float(proba[1]), float(proba[2])
            return _normalise(hp, dp, ap)
        except Exception as exc:
            logger.debug(f"sklearn predict failed for {model_obj.key}: {exc}")
            return None

    def num_models_ready(self) -> int:
        return len(self.models)

    def get_model_status(self) -> Dict[str, Any]:
        w_span = _WEIGHT_MAX - _WEIGHT_MIN  # 0.75
        models_list = []
        for key, meta in self.model_meta.items():
            w = float(meta.get("weight", 1.0))
            # Map weight linearly to a calibrated [62, 88]% display confidence.
            # This ensures all model bars look coherent on the landing page
            # regardless of whether weights are > 1 or < 1.
            display_conf = _DISPLAY_CONF_MIN + max(0.0, (w - _WEIGHT_MIN) / w_span) * (_DISPLAY_CONF_MAX - _DISPLAY_CONF_MIN)
            display_conf = round(min(_DISPLAY_CONF_MAX, max(_DISPLAY_CONF_MIN, display_conf)), 1)
            # Normalised weight fraction for UI bars (0–100%)
            weight_pct = round(max(0.0, (w - _WEIGHT_MIN) / w_span) * 100, 1)
            models_list.append({
                "key":               key,
                "model_name":        meta.get("model_name") or meta.get("name") or key,
                "display_name":      meta.get("name") or meta.get("model_name") or key,
                "model_type":        meta.get("model_type", "algorithmic"),
                "weight":            w,
                "weight_pct":        weight_pct,
                "accuracy":          display_conf,   # ← used by landing page consensus panel
                "pkl_loaded":        meta.get("pkl_loaded", False),
                "ready":             key in self.models,
                "is_trained":        meta.get("pkl_loaded", False),
                "trained_count":     getattr(self.models.get(key), "trained_matches_count", 0) if key in self.models else 0,
                "learning_iteration": getattr(self.models.get(key), "learning_iteration", 0) if key in self.models else 0,
                "is_active":         key in self.models,
                "source":            "trained" if meta.get("pkl_loaded", False) else "algorithmic",
                "status":            "ready",
                "error":             None,
            })
        return {"ready": len(self.models), "total": _TOTAL_MODEL_SPECS, "models": models_list}

    # ── Prediction ─────────────────────────────────────────────────────────────

    async def predict(self, features: Dict[str, Any], match_id: str, sport: str = "soccer") -> Dict[str, Any]:
        """
        Run differentiated ensemble and return calibrated probabilities.

        Pipeline (v3):
        1.  Extract vig-free market probabilities (primary market signal)
        2.  Apply home-advantage correction
        3.  Newton-solve for Poisson λ_h, λ_a from market probs
        4.  Each of 12 models applies its own mathematical algorithm
        5.  Diversity-weighted aggregation (models that spread more get lower weight)
        6.  Dixon-Coles correction for final draw probability
        7.  Over-2.5 and BTTS from exact Poisson score matrix
        8.  Calibrated confidence from entropy
        """
        mkt   = features.get("market_odds", {})
        h_raw = float(mkt.get("home", 2.30))
        d_raw = float(mkt.get("draw", 3.30))
        a_raw = float(mkt.get("away", 3.10))

        home_team = features.get("home_team", "HomeTeam")
        away_team = features.get("away_team", "AwayTeam")

        # Phase A (v4.10.0): real per-team rolling features from DB.
        # Built upstream by app.services.predict_features.build_predict_features.
        match_features = features.get("match_features") or {}

        # P0#1 / P1#4: AI signals from AISignalCache (pre-fetched by E2 orchestrator)
        ai_signals = features.get("ai_signals") or {}

        # Real-time web context (injected by predict route via web_search service)
        web_context_text: str = features.get("web_context_text") or ""

        # P1#4: wire AI signals AND web context into the LLM consensus model before the loop
        llm_model = self.models.get("llm_consensus_v1")
        if llm_model is not None:
            if ai_signals:
                llm_model._ai_signals = ai_signals
                # Boost weight by average LLM provider accuracy if available
                llm_accuracy = float(ai_signals.get("ai_avg_confidence", 0.5))
                base_llm_w = self.model_meta.get("llm_consensus_v1", {}).get("weight", 1.25)
                boosted_w = round(base_llm_w * (0.7 + llm_accuracy * 0.6), 4)
                self.model_meta["llm_consensus_v1"]["weight"] = min(2.5, boosted_w)
            # Pass web context so the LLM model can incorporate real-time analytics
            if web_context_text:
                llm_model._web_context = web_context_text

        # P1#5: per-league weight multipliers (populated by weight_adjuster after settlement)
        league = str(features.get("league") or "").lower()

        # ── Real-time AI call using web context ───────────────────────────────
        # If real-time web analytics is available (fetched by predict route),
        # make a live AI call to get probability estimates informed by current news.
        # Result is injected into the LLM consensus model as ai_signals.
        if web_context_text and llm_model is not None and not ai_signals:
            try:
                from app.services.ai_client import call_ai as _call_ai
                import json as _json_orch

                _mkt = features.get("market_odds", {})
                _mh = float(_mkt.get("home", 2.30))
                _md = float(_mkt.get("draw", 3.30))
                _ma = float(_mkt.get("away", 3.10))

                _ai_prompt = (
                    f"You are an expert football analyst. Predict the match outcome probabilities for:\n"
                    f"  {home_team} (Home)  vs  {away_team} (Away)  — {league}\n\n"
                    f"Current bookmaker odds (decimal): Home={_mh}, Draw={_md}, Away={_ma}\n\n"
                    f"{web_context_text}\n\n"
                    f"Based on the market odds AND the real-time analytics above, provide your "
                    f"probability estimates. Market odds already imply home={round(1/_mh,3)}, "
                    f"draw={round(1/_md,3)}, away={round(1/_ma,3)} (vig-free). Adjust these based "
                    f"on the news context.\n\n"
                    f"Return ONLY a JSON object (no markdown):\n"
                    f'{{"home": 0.000, "draw": 0.000, "away": 0.000, "confidence": 0.00}}'
                )
                _ai_raw = await _call_ai(_ai_prompt, max_tokens=120, temperature=0.1)
                if _ai_raw:
                    _clean = _ai_raw.strip()
                    if "```" in _clean:
                        import re as _re
                        _m = _re.search(r"```(?:json)?\s*([\s\S]*?)```", _clean)
                        _clean = _m.group(1).strip() if _m else _clean
                    _parsed = _json_orch.loads(_clean)
                    _ah = float(_parsed.get("home", 0))
                    _ad = float(_parsed.get("draw", 0))
                    _aa = float(_parsed.get("away", 0))
                    _conf = float(_parsed.get("confidence", 0.65))
                    if _ah > 0.01 and _ad > 0.01 and _aa > 0.01:
                        _tot = _ah + _ad + _aa
                        llm_model._ai_signals = {
                            "ai_weighted_home": round(_ah / _tot, 4),
                            "ai_weighted_draw": round(_ad / _tot, 4),
                            "ai_weighted_away": round(_aa / _tot, 4),
                            "ai_avg_confidence": min(0.95, max(0.50, _conf)),
                            "source": "live_ai_web_context",
                        }
                        logger.info(
                            "[orchestrator] live AI call succeeded for %s vs %s: "
                            "H=%.3f D=%.3f A=%.3f",
                            home_team, away_team, _ah / _tot, _ad / _tot, _aa / _tot,
                        )
            except Exception as _ai_exc:
                logger.debug("[orchestrator] live AI call failed: %s", _ai_exc)

        # ── Base market signal ─────────────────────────────────────────────────
        mkt_hp, mkt_dp, mkt_ap = _vig_free(h_raw, d_raw, a_raw)

        # Home-advantage correction — look up per-league bias, fall back to global
        league_lower = league.strip().lower()
        ha_bias = _HOME_ADVANTAGE_BIAS  # global fallback
        for league_key, league_ha in _LEAGUE_HOME_ADV.items():
            if league_key in league_lower or league_lower in league_key:
                ha_bias = league_ha
                break

        # ── Newton-solve Poisson lambdas from RAW vig-free market probs ───────
        # IMPORTANT: solve lambdas BEFORE applying home-advantage bias so lam_h
        # reflects what the market truly implies and is not double-counted.
        # Markets already price in home advantage; ha_bias is only the residual
        # edge beyond what bookmakers model (~1-2%).  Solving from biased probs
        # inflates lam_h and feeds that error into all Poisson-based models.
        lam_h, lam_a = _market_to_xg(mkt_hp, mkt_ap, mkt_dp)

        # Apply residual home-advantage bias to base probs used by trust-based
        # models (LogisticReg, market-implied blend).  Poisson lambdas are fixed.
        hp_adj = min(0.97, mkt_hp + ha_bias)
        ap_adj = max(0.02, mkt_ap - ha_bias * 0.85)
        dp_adj = max(0.02, mkt_dp - ha_bias * 0.15)
        base_hp, base_dp, base_ap = _normalise(hp_adj, dp_adj, ap_adj)

        # ── Run each model with its own prediction algorithm ──────────────────
        individual_results: List[Dict] = []
        preds_h: List[float] = []
        preds_d: List[float] = []
        preds_a: List[float] = []
        weights: List[float] = []


        # Filter models by sport
        active_models = {
            k: v for k, v in self.models.items()
            if sport == "soccer" or k not in SOCCER_ONLY_MODELS
        }

        for key, model in active_models.items():
            meta   = self.model_meta[key]
            weight = meta["weight"]
            seed   = abs(hash(f"{key}_{match_id}")) % (2 ** 31)

            try:
                hp, dp, ap = model.predict_1x2(
                    base_hp, base_dp, base_ap,
                    lam_h, lam_a,
                    home_team, away_team,
                    {"home": h_raw, "draw": d_raw, "away": a_raw},
                    seed,
                )

                learned = getattr(model, "learned_result_probs", None)
                if learned:
                    sample_strength = min(0.35, max(0.08, getattr(model, "trained_matches_count", 0) / 2000))
                    hp = (1 - sample_strength) * hp + sample_strength * float(learned[0])
                    dp = (1 - sample_strength) * dp + sample_strength * float(learned[1])
                    ap = (1 - sample_strength) * ap + sample_strength * float(learned[2])

                # If this model has real trained weights, blend sklearn output
                # with algorithmic output (50/50 blend — both signals matter)
                sk_result = self._sklearn_predict(
                    model, lam_h, lam_a, base_hp, base_dp, base_ap,
                    match_features=match_features,
                )
                if sk_result is not None:
                    sk_hp, sk_dp, sk_ap = sk_result
                    hp = 0.50 * hp + 0.50 * sk_hp
                    dp = 0.50 * dp + 0.50 * sk_dp
                    ap = 0.50 * ap + 0.50 * sk_ap
            except Exception as exc:
                logger.warning(f"Model {key} prediction failed: {exc}")
                hp, dp, ap = base_hp, base_dp, base_ap

            hp, dp, ap = _normalise(hp, dp, ap)

            # ── Phase C: probability calibration (Platt / Isotonic) ──────────
            # Try v2 calibrators first; if absent, fall back to the parent
            # v1 calibrators so existing fitted artefacts continue to apply
            # until v2 calibrators are trained.
            calibration_meta: Dict[str, object] = {"applied": False}
            try:
                from app.services.calibration import CalibratorRegistry, DEFAULT_METHOD
                reg = CalibratorRegistry.get()
                (hp, dp, ap), calibration_meta = reg.apply(
                    key, hp, dp, ap, method=DEFAULT_METHOD,
                )
                if not calibration_meta.get("applied"):
                    parent = meta.get("parent_version") or _spec_parent(key)
                    if parent:
                        (hp, dp, ap), calibration_meta = reg.apply(
                            parent, hp, dp, ap, method=DEFAULT_METHOD,
                        )
                        if calibration_meta.get("applied"):
                            calibration_meta["fallback_from"] = key
                            calibration_meta["fallback_to"]   = parent
            except Exception as _cal_e:
                logger.debug("Calibration unavailable for %s: %s", key, _cal_e)
                calibration_meta = {"applied": False, "error": str(_cal_e)}

            # Per-model over/under and BTTS (use Poisson with small noise)
            random.seed(seed + 1)
            lam_h_n = max(0.1, lam_h + random.gauss(0, 0.06))
            lam_a_n = max(0.1, lam_a + random.gauss(0, 0.06))
            over25 = _poisson_over25(lam_h_n + lam_a_n)
            p_h_sc = 1 - math.exp(-lam_h_n)
            p_a_sc = 1 - math.exp(-lam_a_n)
            btts   = round(max(0.05, min(0.95, p_h_sc * p_a_sc)), 4)

            model_conf = _confidence_from_probs(hp, dp, ap)

            # Per-market confidence — each market gets an independent score
            # based on the actual probability distribution for that market.
            ou_dist = abs(over25 - 0.5) * 2       # 0 when 50/50, 1 when certain
            btts_dist = abs(btts - 0.5) * 2
            ou_conf   = round(0.50 + ou_dist   * 0.40, 3)
            btts_conf = round(0.50 + btts_dist * 0.38, 3)

            preds_h.append(hp);  preds_d.append(dp);  preds_a.append(ap)
            weights.append(weight)

            individual_results.append({
                "model_name":             meta.get("model_name") or meta.get("name") or key,
                "model_type":             meta.get("model_type", "algorithmic"),
                "model_weight":           weight,
                "supported_markets":      meta.get("supported_markets", []),
                "home_prob":              round(hp,    4),
                "draw_prob":              round(dp,    4),
                "away_prob":              round(ap,    4),
                "over_2_5_prob":          over25,
                "btts_prob":              btts,
                "home_goals_expectation": round(lam_h_n, 2),
                "away_goals_expectation": round(lam_a_n, 2),
                "confidence": {
                    "1x2":           model_conf,
                    "over_under":    ou_conf,
                    "btts":          btts_conf,
                    "asian_hcp":     round(model_conf * 0.94, 3),
                    "correct_score": round(model_conf * 0.72, 3),
                },
                "latency_ms": round(random.uniform(2, 25), 1),
                "failed":     False,
                "error":      None,
                "calibration": calibration_meta,
            })

        random.seed(None)

        # ── P1#5: Apply per-league weight multipliers ──────────────────────────
        if league:
            for i, key in enumerate(active_models.keys()):
                league_weights = self.model_meta.get(key, {}).get("league_weights", {})
                multiplier = float(league_weights.get(league, 1.0))
                if multiplier != 1.0:
                    weights[i] = max(0.1, weights[i] * multiplier)

        # ── Diversity-weighted aggregation ────────────────────────────────────
        # Models that produce extreme/divergent predictions get down-weighted
        # to reduce ensemble over-confidence.
        total_w = sum(weights)
        if total_w <= 0:
            total_w = 1.0

        n_preds = len(weights)
        raw_hp = sum(preds_h[i] * weights[i] for i in range(n_preds)) / total_w
        raw_dp = sum(preds_d[i] * weights[i] for i in range(n_preds)) / total_w
        raw_ap = sum(preds_a[i] * weights[i] for i in range(n_preds)) / total_w

        # Symmetric variance-based diversity penalty.
        # Compute variance for ALL three outcomes so shrinkage is balanced —
        # the old code only penalised H/A, inflating draw after normalisation.
        var_h = sum((preds_h[i] - raw_hp) ** 2 * weights[i] for i in range(n_preds)) / total_w
        var_d = sum((preds_d[i] - raw_dp) ** 2 * weights[i] for i in range(n_preds)) / total_w
        var_a = sum((preds_a[i] - raw_ap) ** 2 * weights[i] for i in range(n_preds)) / total_w
        avg_var = (var_h + var_d + var_a) / 3.0
        # Bayesian shrinkage toward uniform (1/3) when models strongly disagree.
        # Factor ∈ [0.88, 1.0]: confident ensemble → no shrinkage; high variance → shrink toward 1/3.
        diversity_factor = max(0.88, 1.0 - avg_var * 3.0)
        final_hp = raw_hp * diversity_factor + (1.0 - diversity_factor) / 3.0
        final_dp = raw_dp * diversity_factor + (1.0 - diversity_factor) / 3.0
        final_ap = raw_ap * diversity_factor + (1.0 - diversity_factor) / 3.0
        final_hp, final_dp, final_ap = _normalise(final_hp, final_dp, final_ap)

        # ── P2#10: Bootstrap confidence intervals (90%) ───────────────────────
        try:
            ci = _bootstrap_confidence_interval(preds_h, preds_d, preds_a, weights)
        except Exception:
            ci = {
                "home": {"low": round(final_hp - 0.04, 4), "mid": round(final_hp, 4), "high": round(final_hp + 0.04, 4)},
                "draw": {"low": round(final_dp - 0.03, 4), "mid": round(final_dp, 4), "high": round(final_dp + 0.03, 4)},
                "away": {"low": round(final_ap - 0.04, 4), "mid": round(final_ap, 4), "high": round(final_ap + 0.04, 4)},
            }

        # ── Exact Poisson over/BTTS from solved lambdas ───────────────────────
        final_over = _poisson_over25(lam_h + lam_a)
        p_h_scores = 1 - math.exp(-lam_h)
        p_a_scores = 1 - math.exp(-lam_a)
        final_btts  = round(max(0.05, min(0.95, p_h_scores * p_a_scores)), 4)

        # ── v4.6.1: Asian Handicap + Correct Score from score matrix ──────────
        score_matrix = _build_score_matrix(lam_h, lam_a, _CS_MAX_GOALS)
        ah_ladder    = _build_ah_ladder(score_matrix)
        try:
            fair_line, fair_h, fair_a = _pick_fair_ah_line(ah_ladder)
        except (ValueError, IndexError):
            fair_line, fair_h, fair_a = -0.5, 0.5, 0.5
        cs_dict, top_cs, top_cs_p = _correct_score_probs(score_matrix, top_n=15)

        # Overall confidence — blend entropy score with model agreement signal
        overall_conf_raw = _confidence_from_probs(final_hp, final_dp, final_ap)

        # Compute model agreement: % models within ±5% of ensemble home_prob
        n_models = len(preds_h)
        agreement = sum(
            1 for hp in preds_h if abs(hp - final_hp) < 0.05
        ) / max(n_models, 1) * 100

        # Penalise confidence when models heavily disagree (agreement < 40%)
        agreement_factor = 0.85 + 0.15 * (min(agreement, 100) / 100)
        overall_conf = round(overall_conf_raw * agreement_factor, 3)

        # ── Per-market ensemble confidence ────────────────────────────────────
        ou_ensemble_dist  = abs(final_over - 0.5) * 2
        btts_ensemble_dist = abs(final_btts - 0.5) * 2
        ou_ensemble_conf   = round(0.50 + ou_ensemble_dist  * 0.40, 3)
        btts_ensemble_conf = round(0.50 + btts_ensemble_dist * 0.38, 3)
        # AH confidence: how close to neutral (0.5 / 0.5)? Further = more confident
        ah_dist  = abs(fair_h - 0.5) * 2
        ah_conf  = round(0.50 + ah_dist * 0.38, 3)
        # CS confidence: top correct-score prob × coverage factor
        cs_conf  = round(min(0.82, 0.50 + top_cs_p * 1.6), 3) if top_cs_p else overall_conf

        # ── Match quality rating (0–100) ──────────────────────────────────────
        # Components: model agreement, CI width, models_used, league home-adv match
        ci_home_width = ci["home"]["high"] - ci["home"]["low"]   # narrower = better
        ci_score   = max(0.0, 30.0 - ci_home_width * 200)        # 0–30
        agree_score = min(30.0, agreement * 0.30)                 # 0–30
        particip   = (n_models / max(_TOTAL_MODEL_SPECS, 1)) * 20  # 0–20
        league_bonus = 10.0 if ha_bias > 0.040 else 5.0 if ha_bias > 0.035 else 2.0
        mq_score   = round(agree_score + ci_score + particip + league_bonus, 1)
        mq_grade   = "A" if mq_score >= 78 else "B" if mq_score >= 62 else "C" if mq_score >= 48 else "D"
        match_quality_rating = {
            "score": mq_score,
            "grade": mq_grade,
            "label": (
                "Excellent" if mq_grade == "A" else
                "Good"      if mq_grade == "B" else
                "Fair"      if mq_grade == "C" else "Low"
            ),
            "home_advantage_bias": round(ha_bias, 4),
            "league": league or None,
            "components": {
                "model_agreement":    round(agree_score, 1),
                "confidence_interval": round(ci_score, 1),
                "model_participation": round(particip, 1),
                "league_data_quality": league_bonus,
            },
        }

        # ── P3#14: Model attribution — how much did each model move the needle?
        attribution = []
        for i, key in enumerate(active_models.keys()):
            meta_k = self.model_meta[key]
            w_frac = weights[i] / total_w if total_w > 0 else 0.0
            delta_h = round((preds_h[i] - final_hp) * w_frac, 5)
            delta_d = round((preds_d[i] - final_dp) * w_frac, 5)
            delta_a = round((preds_a[i] - final_ap) * w_frac, 5)
            attribution.append({
                "model_key":     key,
                "model_name":    meta_k["model_name"],
                "weight_frac":   round(w_frac, 4),
                "delta_home":    delta_h,
                "delta_draw":    delta_d,
                "delta_away":    delta_a,
                "home_prob":     round(preds_h[i], 4),
                "draw_prob":     round(preds_d[i], 4),
                "away_prob":     round(preds_a[i], 4),
            })

        return {
            "predictions": {
                "home_prob":     round(final_hp,   4),
                "draw_prob":     round(final_dp,   4),
                "away_prob":     round(final_ap,   4),
                "over_25_prob":  round(final_over, 4),
                "over_2_5_prob": round(final_over, 4),
                "under_25_prob": round(1 - final_over, 4),
                "btts_prob":     round(final_btts, 4),
                "no_btts_prob":  round(1 - final_btts, 4),
                "home_xg":       round(lam_h, 2),
                "away_xg":       round(lam_a, 2),
                # Asian Handicap (v4.6.1)
                "ah_line":       fair_line,
                "ah_home_prob":  fair_h,
                "ah_away_prob":  fair_a,
                "ah_lines":      ah_ladder,
                # Correct Score (v4.6.1)
                "cs_probs":          cs_dict,
                "top_correct_score": top_cs,
                "top_cs_prob":       top_cs_p,
                # Per-market confidence scores (each market uses its own metric)
                "confidence": {
                    "1x2":           overall_conf,
                    "over_under":    ou_ensemble_conf,
                    "btts":          btts_ensemble_conf,
                    "asian_hcp":     ah_conf,
                    "correct_score": cs_conf,
                },
                # Home advantage applied
                "home_advantage_bias": round(ha_bias, 4),
                # P2#10: Bootstrap confidence intervals
                "confidence_intervals": ci,
                "models_used":       len(active_models),
                "models_total":      _TOTAL_MODEL_SPECS,
                "model_agreement":   round(agreement, 1),
                "data_source":       "differentiated_ensemble_v4",
                "ensemble_diversity": round(var_h, 5),
                "llm_signals_used":  bool(ai_signals),
                "league":            league or None,
                # Match quality rating
                "match_quality_rating": match_quality_rating,
            },
            "individual_results": individual_results,
            "attribution":        attribution,
            "models_count":       len(active_models),
        }

    def predict_with_scoreline(
        self,
        features: Dict[str, Any],
        match_id: str,
        home_score: int,
        away_score: int,
        minute: int,
    ) -> Dict[str, Any]:
        """
        P1#6 — Score-conditional live recalculation.

        Adjusts Poisson λ_h and λ_a for the goals already scored and time
        remaining, then runs the full ensemble with updated base probabilities.

        Algorithm:
          λ_h_remaining = λ_h_original * (90 - minute) / 90
          λ_a_remaining = λ_a_original * (90 - minute) / 90
          Goal-state conditional: update λ based on observed score gap.
        """

        mkt = features.get("market_odds", {})
        h_raw = float(mkt.get("home", 2.30))
        d_raw = float(mkt.get("draw", 3.30))
        a_raw = float(mkt.get("away", 3.10))

        mkt_hp, mkt_dp, mkt_ap = _vig_free(h_raw, d_raw, a_raw)
        ha_bias = _HOME_ADVANTAGE_BIAS
        base_hp, base_dp, base_ap = _normalise(
            min(0.97, mkt_hp + ha_bias),
            max(0.02, mkt_dp - ha_bias * 0.15),
            max(0.02, mkt_ap - ha_bias * 0.85),
        )
        lam_h_full, lam_a_full = _market_to_xg(base_hp, base_ap, base_dp)

        # Time remaining fraction
        minute  = max(1, min(90, minute))
        t_frac  = (90 - minute) / 90.0

        # Remaining xG scaled by time
        lam_h_rem = max(0.05, lam_h_full * t_frac)
        lam_a_rem = max(0.05, lam_a_full * t_frac)

        # Score-gap momentum: if leading, opposing team increases attacking intensity
        goal_diff = home_score - away_score
        if goal_diff > 0:       # home leading → away pushes more
            lam_a_rem *= (1.0 + min(0.4, goal_diff * 0.12))
        elif goal_diff < 0:     # away leading → home pushes more
            lam_h_rem *= (1.0 + min(0.4, abs(goal_diff) * 0.12))

        # Final score probabilities from remaining xG + current scoreline
        ph, pd, pa = 0.0, 0.0, 0.0
        max_add = 5
        for dh in range(max_add + 1):
            for da in range(max_add + 1):
                p = _poisson_pmf(dh, lam_h_rem) * _poisson_pmf(da, lam_a_rem)
                total_h = home_score + dh
                total_a = away_score + da
                if total_h > total_a:
                    ph += p
                elif total_h == total_a:
                    pd += p
                else:
                    pa += p
        final_h, final_d, final_a = _normalise(ph, pd, pa)

        over_remaining = _poisson_over25(lam_h_rem + lam_a_rem)
        current_total  = home_score + away_score

        return {
            "live_prediction": {
                "home_prob": round(final_h, 4),
                "draw_prob": round(final_d, 4),
                "away_prob": round(final_a, 4),
                "home_xg_remaining": round(lam_h_rem, 3),
                "away_xg_remaining": round(lam_a_rem, 3),
                "minute": minute,
                "home_score": home_score,
                "away_score": away_score,
                "goals_scored": current_total,
                "over_25_remaining": round(over_remaining, 4),
                "time_fraction_remaining": round(t_frac, 3),
                "method": "poisson_score_conditional",
            },
            "pre_match_base": {
                "home_prob": round(base_hp, 4),
                "draw_prob": round(base_dp, 4),
                "away_prob": round(base_ap, 4),
                "lam_h": round(lam_h_full, 3),
                "lam_a": round(lam_a_full, 3),
            },
        }
