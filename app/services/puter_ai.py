"""app/services/puter_ai.py — Puter AI backend provider.

Puter provides free AI access via puter.js (browser) and a REST API (server-side).

Server-side usage requires a Puter bearer token set via PUTER_API_KEY env var.
When the key is absent this module is a no-op — the cascade simply skips it.

REST endpoint: POST https://api.puter.com/drivers/call
Supported drivers: claude-claude-3-5-sonnet, openai-completion (GPT-4o)

Frontend note: puter.js is already loaded in index.html — browser components
can call `puter.ai.chat()` directly for FREE without any server-side key.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_PUTER_URL  = "https://api.puter.com/drivers/call"
_PUTER_DRIVER = "openai-completion"
_PUTER_MODEL  = "gpt-4o-mini"


async def try_puter(prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> Optional[str]:
    """
    Call Puter AI REST API.

    Returns the text response or None if the key is absent / call fails.
    Uses PUTER_API_KEY env var (Puter user bearer token).
    """
    api_key = os.getenv("PUTER_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _PUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "interface": "puter-chat-completion",
                    "driver":    _PUTER_DRIVER,
                    "test_mode": False,
                    "args": {
                        "messages":   [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "model": _PUTER_MODEL,
                    },
                },
            )
            if resp.status_code == 401:
                logger.warning("[puter-ai] invalid API key (401)")
                return None
            if resp.status_code == 429:
                logger.warning("[puter-ai] rate limited (429)")
                return None
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
                logger.debug("[puter-ai] responded (%d chars)", len(text))
                return text
            return None
    except Exception as exc:
        logger.warning("[puter-ai] call failed: %s", exc)
        return None


def puter_configured() -> bool:
    """Return True if PUTER_API_KEY is set (server-side Puter is active)."""
    return bool(os.getenv("PUTER_API_KEY", "").strip())


def puter_status() -> dict:
    """Return status dict compatible with the providers endpoint response format."""
    configured = puter_configured()
    return {
        "configured":           configured,
        "available":            configured,
        "cooling":              False,
        "cooling_for_seconds":  0,
        "failing":              False,
        "last_error_code":      None,
        "browser_available":    True,
        "note": (
            "Browser AI active via puter.js (free, no key needed). "
            "Set PUTER_API_KEY for server-side agent use."
        ) if not configured else "Server-side active",
    }
