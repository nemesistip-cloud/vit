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

    @staticmethod
    def _prediction_features(kwargs: dict) -> Optional[Dict[str, Any]]:
        """Return caller-supplied structured match evidence, never synthetic odds."""
        for key in ("features", "feature_vector", "match_data"):
            value = kwargs.get(key)
            if isinstance(value, dict) and value:
                return value

        features: Dict[str, Any] = {}
        for key in ("market_odds", "home_team", "away_team", "league", "match_features"):
            value = kwargs.get(key)
            if value not in (None, {}, []):
                features[key] = value
        return features or None

    def _unavailable_response(self, message: str, model_id: str, start_time: float) -> Dict[str, Any]:
        response = self._wrap_response(message, "unavailable", model_id, start_time, is_fallback=True)
        response["status"] = "unavailable"
        return response

    async def _local_prediction_fallback(
        self,
        kwargs: dict,
        model_id: str,
        start_time: float,
    ) -> Dict[str, Any]:
        features = self._prediction_features(kwargs)
        if not features:
            return self._unavailable_response(
                "No match data was supplied, so a local prediction fallback cannot be generated.",
                model_id,
                start_time,
            )

        orch = get_orchestrator()
        if not orch:
            return self._unavailable_response(
                "The VIT AI service is unavailable and no local prediction engine is ready.",
                model_id,
                start_time,
            )

        try:
            result = await orch.predict(features, "gateway_fallback")
            pred = result.get("predictions", result)
            required = ("home_prob", "draw_prob", "away_prob")
            if not isinstance(pred, dict) or any(pred.get(key) is None for key in required):
                raise ValueError("local prediction engine returned incomplete probabilities")
            formatted = (
                "Local prediction fallback (based on supplied match inputs; not an LLM response): "
                f"Home={pred['home_prob']}, Draw={pred['draw_prob']}, Away={pred['away_prob']}."
            )
            return self._wrap_response(formatted, "local_orchestrator", model_id, start_time, is_fallback=True)
        except Exception as exc:
            logger.warning("[AIGateway] Local prediction fallback failed: %s", exc)
            return self._unavailable_response(
                "The VIT AI service and local prediction fallback are unavailable.",
                model_id,
                start_time,
            )

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
                    logger.warning(f"[AIGateway] External call failed: {e}")
            if intent == "prediction":
                return await self._local_prediction_fallback(kwargs, manual_model_id, t0)
            return self._unavailable_response(
                "The requested AI model is unavailable; a prediction model cannot substitute for conversational reasoning.",
                manual_model_id,
                t0,
            )

        # ── 2. Fastest Routing Mode ─────────────────────────────────────────
        if mode == "fastest":
            logger.info("[AIGateway] Fastest route selected.")
            if intent == "prediction":
                return await self._local_prediction_fallback(kwargs, "local_fast", t0)
            return self._unavailable_response(
                "The local fast route requires structured prediction inputs and cannot answer a general chat request.",
                "local_fast",
                t0,
            )

        # ── 3. Cheapest Routing Mode ────────────────────────────────────────
        if mode == "cheapest":
            logger.info("[AIGateway] Cheapest route selected.")
            if intent == "prediction":
                return await self._local_prediction_fallback(kwargs, "local_market_fallback", t0)
            return self._unavailable_response(
                "The local route only supports predictions with supplied structured match inputs.",
                "local_market_fallback",
                t0,
            )

        # ── 4. Highest Accuracy Mode ────────────────────────────────────────
        if mode == "highest_accuracy" or mode == "accuracy":
            logger.info("[AIGateway] Accuracy route selected; no accuracy advantage is assumed.")
            try:
                response = await vit_ai_client.call_ai(prompt, routing="accuracy", intent=intent, model="llm_consensus_v1", **kwargs)
                return self._wrap_response(response, "vit-ai", "llm_consensus_v1", t0)
            except Exception as e:
                logger.warning(f"[AIGateway] Microservice accuracy route failed: {e}")
                if intent == "prediction":
                    return await self._local_prediction_fallback(kwargs, "local_market_fallback", t0)
                return self._unavailable_response(
                    "The VIT AI service is unavailable; no accuracy-verified conversational fallback is configured.",
                    "llm_consensus_v1",
                    t0,
                )

        # ── 5. Default Ensemble / Consensus Mode ────────────────────────────
        target_model = kwargs.get("model") or ("ensemble_v1" if intent == "prediction" else "llm_consensus_v1")
        logger.info(f"[AIGateway] Ensemble consensus route activated for model {target_model}.")

        try:
            kwargs_clean = {k: v for k, v in kwargs.items() if k != "intent"}
            response = await vit_ai_client.call_ai(prompt, model=target_model, intent=intent, **kwargs_clean)
            return self._wrap_response(response, "vit-ai", target_model, t0)
        except Exception as e:
            logger.warning(f"[AIGateway] External call failed. Falling back to local orchestrator: {e}")

        if intent == "prediction":
            return await self._local_prediction_fallback(kwargs, "local_market_fallback", t0)
        return self._unavailable_response(
            "VIT AI is temporarily unavailable. No conversational response was generated; please try again later.",
            target_model,
            t0,
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
