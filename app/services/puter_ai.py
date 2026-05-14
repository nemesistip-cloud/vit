"""app/services/puter_ai.py — Puter AI backend provider.

Puter provides free AI access via puter.js (browser) and a REST API (server-side).

Server-side usage requires a Puter bearer token set via PUTER_API_KEY env var.
When the key is absent this module is a no-op — the cascade simply skips it.

REST endpoint: POST https://api.puter.com/drivers/call

Supported server-side drivers:
  - openai-completion   → gpt-4o-mini, gpt-4o
  - claude-claude-3-5-sonnet → claude-3-5-sonnet

Browser (puter.js — FREE, no key needed):
  - puter.ai.chat("msg")                          → Claude claude-3-5-sonnet (default)
  - puter.ai.chat("msg", {model:"gpt-4o"})        → OpenAI GPT-4o
  - puter.ai.chat("msg", {model:"meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"})
  - puter.ai.chat("msg", {model:"mistral-large-latest"})
  - puter.ai.chat("msg", {model:"google/gemma-2-27b-it"})

Frontend note: puter.js is already loaded in index.html — browser components
can call `puter.ai.chat()` directly for FREE without any server-side key.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_PUTER_URL = "https://api.puter.com/drivers/call"

_PUTER_DRIVERS = [
    {"interface": "puter-chat-completion", "driver": "openai-completion", "model": "gpt-4o-mini"},
    {"interface": "puter-chat-completion", "driver": "claude-claude-3-5-sonnet", "model": "claude-3-5-sonnet"},
    {"interface": "puter-chat-completion", "driver": "openai-completion", "model": "gpt-4o"},
]

PUTER_BROWSER_MODELS = [
    {"model": "claude-3-5-sonnet", "label": "Claude 3.5 Sonnet (free via Puter)"},
    {"model": "gpt-4o", "label": "GPT-4o (free via Puter)"},
    {"model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "label": "Llama 3.1 70B (free via Puter)"},
    {"model": "mistral-large-latest", "label": "Mistral Large (free via Puter)"},
    {"model": "google/gemma-2-27b-it", "label": "Gemma 2 27B (free via Puter)"},
]


async def try_puter(prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> Optional[str]:
    """
    Call Puter AI REST API — tries each driver in order until one succeeds.

    Returns the text response or None if the key is absent / all calls fail.
    Uses PUTER_API_KEY env var (Puter user bearer token).
    """
    api_key = os.getenv("PUTER_API_KEY", "").strip()
    if not api_key:
        return None

    for driver_cfg in _PUTER_DRIVERS:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    _PUTER_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "interface": driver_cfg["interface"],
                        "driver":    driver_cfg["driver"],
                        "test_mode": False,
                        "args": {
                            "messages":    [{"role": "user", "content": prompt}],
                            "max_tokens":  max_tokens,
                            "temperature": temperature,
                            "model":       driver_cfg["model"],
                        },
                    },
                )
                if resp.status_code == 401:
                    logger.warning("[puter-ai] invalid API key (401)")
                    return None
                if resp.status_code == 429:
                    logger.warning("[puter-ai] rate limited (429)")
                    continue
                if resp.status_code >= 400:
                    logger.warning("[puter-ai] driver %s HTTP %d — trying next", driver_cfg["driver"], resp.status_code)
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = (
                    data.get("result", {})
                        .get("message", {})
                        .get("content", "")
                    or data.get("result", {})
                        .get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                )
                if text:
                    logger.debug("[puter-ai] %s responded (%d chars)", driver_cfg["model"], len(text))
                    return text
        except Exception as exc:
            logger.warning("[puter-ai] driver %s failed: %s — trying next", driver_cfg["driver"], exc)
            continue

    logger.warning("[puter-ai] all drivers failed")
    return None


def puter_configured() -> bool:
    """Return True if PUTER_API_KEY is set (server-side Puter is active)."""
    return bool(os.getenv("PUTER_API_KEY", "").strip())


def puter_status() -> dict:
    """Return status dict compatible with the providers endpoint response format."""
    configured = puter_configured()
    return {
        "configured":          configured,
        "available":           configured,
        "cooling":             False,
        "cooling_for_seconds": 0,
        "failing":             False,
        "last_error_code":     None,
        "browser_available":   True,
        "browser_models":      [m["label"] for m in PUTER_BROWSER_MODELS],
        "note": (
            "Browser AI active via puter.js (free — Claude 3.5, GPT-4o, Llama 3.1, Mistral Large). "
            "Set PUTER_API_KEY for server-side agent use."
        ) if not configured else "Server-side + browser active. Models: GPT-4o-mini, Claude 3.5 Sonnet.",
    }
