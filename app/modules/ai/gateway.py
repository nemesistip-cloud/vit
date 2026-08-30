"""AI Gateway with Intelligent Routing Strategies.
VIT Platform v6.0.0
"""
from __future__ import annotations
import logging
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.dependencies import get_orchestrator
from app.services.vit_ai_client import vit_ai_client
from app.modules.ai.registry import MODEL_SPECS

logger = logging.getLogger(__name__)

class AIGateway:
    """The central routing entrypoint for all AI intelligence requests across the VIT Platform.

    Supports:
      - Local model ensemble (ModelOrchestrator)
      - External microservice calls (VitAIClient)
      - Advanced routing modes (Fastest, Cheapest, Highest Accuracy, Ensemble, Manual)
    """
    _instance: Optional[AIGateway] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info("[AIGateway] Central AI Routing Gateway initialized.")

    def detect_intent(self, prompt: str, kwargs: dict) -> str:
        """Determines whether a query is a feature-based prediction or general conversational AI request."""
        if kwargs.get("intent") in ["prediction", "conversational"]:
            return kwargs.get("intent")

        if any(k in kwargs for k in ["market_odds", "features", "feature_vector", "match_data"]):
            return "prediction"

        p = prompt.lower().strip()
        prediction_signals = ["home_prob", "away_prob", "draw_prob", "xg_", "btts_prob", "odds:", "1x2:", "predict match", "feature_matrix"]
        if any(sig in p for sig in prediction_signals):
            return "prediction"

        return "conversational"

    async def route_chat(
        self,
        prompt: str,
        routing_mode: str = "ensemble",
        manual_model_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Routes a natural language chat query based on the selected mode and detected intent."""
        t0 = time.monotonic()
        mode = routing_mode.lower()
        intent = self.detect_intent(prompt, kwargs)

        logger.info(f"[AIGateway] Routing chat via mode '{mode}' (detected intent: {intent})...")

        # ── 1. Manual Routing Mode ──────────────────────────────────────────
        if mode == "manual" and manual_model_id:
            logger.info(f"[AIGateway] Manual route triggered for model {manual_model_id}")
            if "llm" in manual_model_id or manual_model_id == "vit-ai":
                try:
                    kwargs_clean = {k: v for k, v in kwargs.items() if k != "intent"}
                    response = await vit_ai_client.call_ai(prompt, model=manual_model_id, intent=intent, **kwargs_clean)
                    return self._wrap_response(response, "vit-ai", manual_model_id, t0)
                except Exception as e:
                    logger.warning(f"[AIGateway] External call failed, falling back to local ensemble: {e}")

            orch = get_orchestrator()
            if orch:
                try:
                    res = await orch.predict({"prompt": prompt, "market_odds": kwargs.get("market_odds") or {"home": 2.0, "draw": 3.0, "away": 3.5}}, "manual_gate_id")
                    pred = res.get("predictions", {})
                    formatted = f"Ensemble prediction: Win probability Home={pred.get('home_prob')}, Draw={pred.get('draw_prob')}, Away={pred.get('away_prob')}"
                    return self._wrap_response(formatted, "local_orchestrator", manual_model_id, t0)
                except Exception:
                    pass

        # ── 2. Fastest Routing Mode ─────────────────────────────────────────
        if mode == "fastest":
            logger.info("[AIGateway] Fastest route chosen. Routing directly to local XGBoost / Logistic regressor.")
            orch = get_orchestrator()
            if orch:
                res = await orch.predict({"prompt": prompt, "market_odds": kwargs.get("market_odds") or {"home": 2.0, "draw": 3.0, "away": 3.5}}, "fastest_gate_id")
                pred = res.get("predictions", {})
                formatted = f"Fast-route prediction generated. Home Win Prob: {pred.get('home_prob', 0)*100:.1f}%, Draw: {pred.get('draw_prob', 0)*100:.1f}%, Away: {pred.get('away_prob', 0)*100:.1f}%."
                return self._wrap_response(formatted, "local_orchestrator", "xgb_v2", t0)

        # ── 3. Cheapest Routing Mode ────────────────────────────────────────
        if mode == "cheapest":
            logger.info("[AIGateway] Cheapest route chosen. Routing locally to preserve external tokens.")
            orch = get_orchestrator()
            if orch:
                res = await orch.predict({"prompt": prompt, "market_odds": kwargs.get("market_odds") or {"home": 2.0, "draw": 3.0, "away": 3.5}}, "cheapest_gate_id")
                pred = res.get("predictions", {})
                formatted = f"Cheapest local route: Home={pred.get('home_prob')} | Draw={pred.get('draw_prob')} | Away={pred.get('away_prob')}"
                return self._wrap_response(formatted, "local_orchestrator", "poisson_v2", t0)

        # ── 4. Highest Accuracy Mode ────────────────────────────────────────
        if mode == "highest_accuracy" or mode == "accuracy":
            logger.info("[AIGateway] Highest accuracy route chosen. Delegating to LLM Consensus microservice.")
            try:
                response = await vit_ai_client.call_ai(prompt, routing="accuracy", intent=intent, model="llm_consensus_v1", **kwargs)
                return self._wrap_response(response, "vit-ai", "llm_consensus_v1", t0)
            except Exception as e:
                logger.warning(f"[AIGateway] Microservice accuracy route failed: {e}")

        # ── 5. Default Ensemble / Consensus Mode ────────────────────────────
        target_model = kwargs.get("model") or ("ensemble_v1" if intent == "prediction" else "llm_consensus_v1")
        logger.info(f"[AIGateway] Ensemble consensus route activated for model {target_model}.")

        try:
            kwargs_clean = {k: v for k, v in kwargs.items() if k != "intent"}
            response = await vit_ai_client.call_ai(prompt, model=target_model, intent=intent, **kwargs_clean)
            return self._wrap_response(response, "vit-ai", target_model, t0)
        except Exception as e:
            logger.warning(f"[AIGateway] External call failed. Falling back to local orchestrator: {e}")

        orch = get_orchestrator()
        if orch:
            try:
                from app.services.ai_client import call_ai as call_ai_local
                kwargs_clean = {k: v for k, v in kwargs.items() if k != "intent"}
                response = await call_ai_local(prompt, intent=intent, **kwargs_clean)
                return self._wrap_response(response, "local_orchestrator", "ensemble_v2", t0, is_fallback=True)
            except Exception as e:
                logger.error(f"[AIGateway] Local ensemble fallback failed: {e}")

        return self._wrap_response(
            "Intelligence layer is offline. Running on offline failover buffer.",
            "fallback_buffer",
            "offline_heuristic",
            t0,
            is_fallback=True
        )

    def _wrap_response(self, text: str, provider: str, model_id: str, start_time: float, is_fallback: bool = False) -> Dict[str, Any]:
        latency_ms = round((time.monotonic() - start_time) * 1000)
        status = "fallback" if is_fallback or provider == "fallback_buffer" else "success"
        return {
            "response": text,
            "completion": text,
            "provider": provider,
            "model_id": model_id,
            "latency_ms": latency_ms,
            "timestamp": int(time.time()),
            "status": status,
            "is_fallback": is_fallback or (provider == "fallback_buffer")
        }

ai_gateway = AIGateway()
