"""app/services/ai_client.py — Unified multi-provider AI client for backend agents.

Provider cascade (tried in order until one succeeds):
  1. Gemini   (GEMINI_API_KEY)   — gemini-2.0-flash → gemini-2.0-flash-lite → gemini-1.5-flash
  2. Claude   (CLAUDE_API_KEY)   — claude-3-5-haiku-20241022 → claude-3-haiku-20240307
  3. OpenAI   (OPENAI_API_KEY)   — gpt-4o-mini → gpt-3.5-turbo
  4. xAI/Grok (XAI_API_KEY)      — grok-2-latest → grok-beta

Rate-limit handling:
  - On HTTP 429: exponential backoff (2 s → 4 s → 8 s) then try next provider.
  - Per-provider backoff state is module-level so ALL agents share it.
  - Provider marked as "cooling" for backoff_until timestamp; skipped until then.
  - On 404 (model not found): skip to next model in same provider's list.

Usage in agents:
    from app.services.ai_client import call_ai
    raw = await call_ai(prompt, max_tokens=512)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── Model lists ────────────────────────────────────────────────────────────────

_GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]
_CLAUDE_MODELS = [
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
]
_OPENAI_MODELS = [
    "gpt-4o-mini",
    "gpt-3.5-turbo",
]
_GROQ_MODELS = [
    "grok-2",
    "grok-beta",
    "grok-2-1212",
]

# ── Backoff state (module-level — shared across all agents) ────────────────────

_backoff_until: dict[str, float] = {}
_provider_failures: dict[str, dict] = {}  # tracks non-rate-limit errors (401, 400, etc.)   # provider_name → unix timestamp
_BACKOFF_SECONDS = [2, 4, 8, 16]        # escalating waits on 429

# ── Dynamic provider priority (hot-reloadable) ─────────────────────────────────

_DEFAULT_PRIORITY = ["gemini", "claude", "openai", "grok"]
_provider_priority: list[str] = list(_DEFAULT_PRIORITY)


def get_provider_priority() -> list[str]:
    """Return current provider try-order."""
    return list(_provider_priority)


def set_provider_priority(order: list[str]) -> list[str]:
    """
    Set the provider try-order.  Unknown names are ignored; missing names
    are appended at the end so no provider is ever silently dropped.
    """
    global _provider_priority
    known = set(_DEFAULT_PRIORITY)
    clean = [p for p in order if p in known]
    for p in _DEFAULT_PRIORITY:
        if p not in clean:
            clean.append(p)
    _provider_priority = clean
    logger.info("[ai-client] provider priority updated: %s", clean)
    return list(_provider_priority)


def get_provider_failures() -> dict[str, dict]:
    """Return a copy of current non-rate-limit provider failures (401/400/403)."""
    return dict(_provider_failures)


def reset_provider_backoff(name: str | None = None) -> dict[str, float]:
    """
    Clear rate-limit backoff AND non-rate-limit failure tracking for one provider or all.
    Returns the cleared backoff entries.  Env keys are re-read on every call so no
    restart is needed after rotating an API secret in the environment.
    """
    global _backoff_until
    if name:
        cleared = {name: _backoff_until.pop(name, 0.0)}
        _provider_failures.pop(name, None)
    else:
        cleared = dict(_backoff_until)
        _backoff_until.clear()
        _provider_failures.clear()
    logger.info("[ai-client] backoff+failures reset for: %s", list(cleared.keys()) or "all")
    return cleared


def _provider_available(name: str) -> bool:
    return time.monotonic() >= _backoff_until.get(name, 0.0)


def _mark_provider_failed(name: str, status_code: int) -> None:
    """Track non-rate-limit failures (400, 401, 403) so provider_status() can expose them."""
    import time as _time
    _provider_failures[name] = {
        "status_code": status_code,
        "failed_at": _time.time(),
    }
    logger.warning("[ai-client] %s returned HTTP %d — marked as failing", name, status_code)


def _mark_rate_limited(name: str, retry_after: Optional[str] = None) -> None:
    wait = 8.0
    if retry_after:
        try:
            wait = max(float(retry_after), 4.0)
        except ValueError:
            pass
    _backoff_until[name] = time.monotonic() + wait
    logger.warning("[ai-client] %s rate-limited — cooling for %.0fs", name, wait)


# ── Provider implementations ───────────────────────────────────────────────────

async def _try_gemini(prompt: str, max_tokens: int, temperature: float) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or not _provider_available("gemini"):
        return None

    base = "https://generativelanguage.googleapis.com/v1beta/models"
    for model in _GEMINI_MODELS:
        url = f"{base}/{model}:generateContent?key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                resp = await client.post(url, json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                    },
                })
                if resp.status_code == 404:
                    continue
                if resp.status_code == 429:
                    _mark_rate_limited("gemini", resp.headers.get("Retry-After"))
                    return None
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                logger.debug("[ai-client] gemini/%s responded (%d chars)", model, len(text))
                return text
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            logger.warning("[ai-client] gemini/%s HTTP %d", model, sc)
            if sc in (400, 401, 403):
                _mark_provider_failed("gemini", sc)
        except Exception as e:
            logger.warning("[ai-client] gemini/%s error: %s", model, e)
    return None


async def _try_claude(prompt: str, max_tokens: int, temperature: float) -> str | None:
    api_key = os.getenv("CLAUDE_API_KEY", "").strip()
    if not api_key or not _provider_available("claude"):
        return None

    url = "https://api.anthropic.com/v1/messages"
    for model in _CLAUDE_MODELS:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                if resp.status_code == 404:
                    continue
                if resp.status_code == 429:
                    _mark_rate_limited("claude", resp.headers.get("Retry-After"))
                    return None
                if resp.status_code == 529:  # Anthropic overloaded
                    _mark_rate_limited("claude", "10")
                    return None
                resp.raise_for_status()
                data = resp.json()
                text = data["content"][0]["text"]
                logger.debug("[ai-client] claude/%s responded (%d chars)", model, len(text))
                return text
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            logger.warning("[ai-client] claude/%s HTTP %d", model, sc)
            if sc in (400, 401, 403):
                _mark_provider_failed("claude", sc)
        except Exception as e:
            logger.warning("[ai-client] claude/%s error: %s", model, e)
    return None


async def _try_openai(prompt: str, max_tokens: int, temperature: float) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or not _provider_available("openai"):
        return None

    url = "https://api.openai.com/v1/chat/completions"
    for model in _OPENAI_MODELS:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                if resp.status_code == 404:
                    continue
                if resp.status_code == 429:
                    _mark_rate_limited("openai", resp.headers.get("Retry-After"))
                    return None
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
                logger.debug("[ai-client] openai/%s responded (%d chars)", model, len(text))
                return text
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            logger.warning("[ai-client] openai/%s HTTP %d", model, sc)
            if sc in (400, 401, 403):
                _mark_provider_failed("openai", sc)
        except Exception as e:
            logger.warning("[ai-client] openai/%s error: %s", model, e)
    return None


async def _try_grok(prompt: str, max_tokens: int, temperature: float) -> str | None:
    api_key = os.getenv("XAI_API_KEY", "").strip()
    if not api_key or not _provider_available("grok"):
        return None

    url = "https://api.x.ai/v1/chat/completions"
    for model in _GROQ_MODELS:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                if resp.status_code == 404:
                    continue
                if resp.status_code == 429:
                    _mark_rate_limited("grok", resp.headers.get("Retry-After"))
                    return None
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
                logger.debug("[ai-client] grok/%s responded (%d chars)", model, len(text))
                return text
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            logger.warning("[ai-client] grok/%s HTTP %d", model, sc)
            if sc in (400, 401, 403):
                _mark_provider_failed("grok", sc)
        except Exception as e:
            logger.warning("[ai-client] grok/%s error: %s", model, e)
    return None


# ── Public API ─────────────────────────────────────────────────────────────────

async def call_ai_with_provider(
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.2,
    preferred: str | None = None,
) -> tuple[str, str] | None:
    """
    Like call_ai() but returns (text, provider_name) on success, or None on failure.
    Use this when you need to record which provider produced the response.
    """
    _fn_map = {
        "gemini": _try_gemini,
        "claude": _try_claude,
        "openai": _try_openai,
        "grok":   _try_grok,
    }
    providers = [(n, _fn_map[n]) for n in _provider_priority if n in _fn_map]
    if preferred and preferred in _fn_map:
        providers.sort(key=lambda p: 0 if p[0] == preferred else 1)

    for name, fn in providers:
        if not _provider_available(name):
            logger.debug("[ai-client] skipping %s (cooling down)", name)
            continue
        result = await fn(prompt, max_tokens, temperature)
        if result:
            return result, name

    logger.error("[ai-client] all providers failed for prompt (len=%d)", len(prompt))
    return None


async def call_ai(
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.2,
    preferred: str | None = None,
) -> str | None:
    """
    Call the best available AI provider and return the text response.

    Tries providers in order: Gemini → Claude → OpenAI → xAI/Grok.
    Rate-limited providers are skipped and retried next cycle.
    Returns None if all providers are unavailable or fail.

    Args:
        prompt:      The full prompt string to send.
        max_tokens:  Maximum response tokens (default 512).
        temperature: Sampling temperature (default 0.2 for structured tasks).
        preferred:   Optional override to try a specific provider first
                     ("gemini" | "claude" | "openai" | "grok").
    """
    _fn_map = {
        "gemini": _try_gemini,
        "claude": _try_claude,
        "openai": _try_openai,
        "grok":   _try_grok,
    }
    providers = [(n, _fn_map[n]) for n in _provider_priority if n in _fn_map]

    # Move preferred provider to front if specified
    if preferred and preferred in _fn_map:
        providers.sort(key=lambda p: 0 if p[0] == preferred else 1)

    for name, fn in providers:
        if not _provider_available(name):
            logger.debug("[ai-client] skipping %s (cooling down)", name)
            continue
        result = await fn(prompt, max_tokens, temperature)
        if result:
            return result

    logger.error("[ai-client] all providers failed or unavailable for prompt (len=%d)", len(prompt))
    return None


def provider_status() -> dict[str, dict]:
    """Return current availability status of all providers."""
    now = time.monotonic()
    keys = {
        "gemini": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "claude": bool(os.getenv("CLAUDE_API_KEY", "").strip()),
        "openai": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "grok":   bool(os.getenv("XAI_API_KEY", "").strip()),
    }
    result = {}
    for name, has_key in keys.items():
        cooling_until = _backoff_until.get(name, 0.0)
        cooling = cooling_until > now
        failure = _provider_failures.get(name)
        failing = bool(failure)
        result[name] = {
            "configured": has_key,
            "available": has_key and not cooling and not failing,
            "cooling": cooling,
            "cooling_for_seconds": max(0, round(cooling_until - now, 1)) if cooling else 0,
            "failing": failing,
            "last_error_code": failure["status_code"] if failure else None,
        }
    return result
