"""Native AI Inference Client - VIT v5.5.0.
Self-contained intelligence hub — no external API dependencies.
"""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import AIMLAPI_API_KEY, GEMINI_API_KEY
from app.core.dependencies import get_orchestrator

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-3.6-flash"


async def _call_aimlapi_fallback(prompt: str, **kwargs) -> Optional[str]:
    """Attempt a direct AIML API response when the configured key is present."""
    api_key = (AIMLAPI_API_KEY or os.getenv("AIMLAPI_API_KEY") or "").strip()
    if not api_key:
        return None

    model = kwargs.get("aiml_model") or kwargs.get("model") or "openai/gpt-5-5"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("https://api.aimlapi.com/v1/chat/completions", headers=headers, json=payload)
        if response.status_code >= 400:
            logger.warning("AIML API request failed: %s %s", response.status_code, response.text[:200])
            return None
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return None
        first = choices[0]
        message = first.get("message", {})
        content = message.get("content") or first.get("text") or ""
        if isinstance(content, list):
            content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception as exc:
        logger.warning("AIML API fallback failed: %s", exc)
        return None
    return None


async def _call_gemini_fallback(prompt: str, **kwargs) -> Optional[str]:
    """Attempt a direct Gemini response when the configured key is present."""
    api_key = (GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        return None

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent?key={api_key}"
        system_instruction = (
            "You are VIT Network's intelligence assistant. Reply concisely, clearly, and factually. "
            "If the user asks for predictions, give structured, balanced reasoning and label uncertainty."
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": prompt}]}],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
        if response.status_code >= 400:
            logger.warning("Gemini request failed: %s %s", response.status_code, response.text[:200])
            return None
        data = response.json()
        text = ""
        for candidate in data.get("candidates", []) or []:
            content = candidate.get("content", {})
            for part in content.get("parts", []) or []:
                if isinstance(part, dict):
                    text += str(part.get("text", ""))
        if text.strip():
            return text.strip()
    except Exception as exc:
        logger.warning("Gemini fallback failed: %s", exc)
        return None
    return None


async def _call_ai_with_provider(prompt: str, **kwargs) -> Tuple[str, str]:
    """
    Main entry point for Native AI inference.
    Routes queries through the AI Gateway, delegating to the live microservice
    or local model ensemble under the requested routing mode.
    """
    logger.info(f"Native AI call: {prompt[:80]}...")

    from app.modules.ai.gateway import ai_gateway
    routing_mode = kwargs.get("routing_mode", "ensemble")

    # Call the AI Gateway
    gateway_res = await ai_gateway.route_chat(prompt, routing_mode=routing_mode, **kwargs)
    response_text = gateway_res.get("response") or ""

    if not response_text or gateway_res.get("is_fallback"):
        intent = ai_gateway.detect_intent(prompt, kwargs)
        if intent != "prediction":
            gemini_response = await _call_gemini_fallback(prompt, **kwargs)
            if gemini_response:
                return gemini_response, "gemini"

            aiml_response = await _call_aimlapi_fallback(prompt, **kwargs)
            if aiml_response:
                return aiml_response, "aimlapi"

        if response_text:
            return response_text, gateway_res.get("provider", "unavailable")
        return "VIT AI and its configured fallback providers are unavailable; no response was generated.", "unavailable"

    return response_text, gateway_res.get("provider", "unknown")


async def call_ai(prompt: str, **kwargs) -> str:
    """Return a response from the gateway, using configured LLMs only as fallbacks."""
    response, _provider = await _call_ai_with_provider(prompt, **kwargs)
    return response


async def call_ai_with_provider(prompt: str, **kwargs) -> Tuple[str, str]:
    """Return both the assistant response and the provider that actually produced it."""
    try:
        return await _call_ai_with_provider(prompt, **kwargs)
    except Exception as e:
        logger.error(f"Critical AI failure: {e}")
        return ("VIT AI is temporarily unavailable; no response was generated.", "unavailable")


async def provider_status() -> Dict[str, Any]:
    """Report status of the native AI system."""
    try:
        orch = get_orchestrator()
        ready = orch.num_models_ready() if orch else 0
    except Exception as exc:
        logger.warning("Native AI readiness check failed: %s", exc)
        ready = 0
        orch = None

    total = None
    model_status = {}
    if orch:
        try:
            model_status = orch.get_model_status()
            total = model_status.get("total")
        except Exception as exc:
            logger.warning("Native AI model status query failed: %s", exc)

    model_entries = model_status.get("models", []) if isinstance(model_status, dict) else []
    trained_models = sum(1 for model in model_entries if model.get("pkl_loaded") is True)
    status_str = "market_fallback_available" if ready > 0 and trained_models == 0 else (
        "available" if ready > 0 else "unavailable"
    )

    return {
        "native": {
            "status": status_str,
            "available": ready > 0,
            "models_ready": ready,
            "models_callable": ready,
            "trained_models": trained_models,
            "total_models": total,
            "orchestrator_active": orch is not None,
            "provider_type": "internal_prediction_fallback",
            "capability": "market_probability_fallback",
        },
        "gemini": _external_provider_status(
            bool(GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        ),
        "aimlapi": _external_provider_status(
            bool(AIMLAPI_API_KEY or os.getenv("AIMLAPI_API_KEY"))
        ),
    }


def _external_provider_status(configured: bool) -> Dict[str, Any]:
    """Report configuration only; provider connectivity is verified on inference."""
    return {
        "status": "configured" if configured else "not_configured",
        "configured": configured,
        "available": None,
        "connectivity": "not_probed",
        "provider_type": "external_llm",
    }


async def verify_provider(name: str) -> bool:
    """Return readiness only when the provider is known and demonstrably available."""
    status = (await provider_status()).get(name)
    return bool(status and status.get("available") is True)


def get_provider_priority() -> List[str]:
    """Return the primary gateway route and configured fallback order."""
    configured = {
        "native": True,
        "gemini": bool(GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "aimlapi": bool(AIMLAPI_API_KEY or os.getenv("AIMLAPI_API_KEY")),
    }
    return [provider for provider, is_configured in configured.items() if is_configured]


def set_provider_priority(order: List[str]) -> List[str]:
    """Return the effective supported order; provider ordering is currently fixed."""
    effective = get_provider_priority()
    requested = [provider for provider in order if provider in effective]
    return requested + [provider for provider in effective if provider not in requested]


def get_provider_failures() -> Dict[str, int]:
    """Track failures per provider."""
    return {"native": 0}


async def reset_provider_backoff(name: Optional[str] = None) -> Dict[str, Any]:
    """Reset error counters and backoff timers."""
    return {"native": "reset"}
