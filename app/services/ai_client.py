"""app/services/ai_client.py — Unified multi-provider AI client for backend agents.

Provider cascade (tried in order until one succeeds):
  1. Gemini   (GEMINI_API_KEY)    — gemini-2.0-flash → gemini-2.0-flash-lite → gemini-1.5-flash
  2. Claude   (CLAUDE_API_KEY)    — claude-3-5-haiku-20241022 → claude-3-haiku-20240307
  3. OpenAI   (OPENAI_API_KEY)    — gpt-4o-mini → gpt-3.5-turbo
  4. DeepSeek (DEEPSEEK_API_KEY)  — deepseek-chat → deepseek-reasoner
  5. xAI/Grok (XAI_API_KEY)       — grok-3-mini → grok-2-1212
  6. Puter    (PUTER_API_KEY)     — GPT-4o-mini via puter.com (optional free tier)

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
from app.services.cache import cache
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── Model lists ──────────────────────────────────────────────────────────────

_GEMINI_MODELS = [
    "gemini-1.5-pro",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]
_CLAUDE_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
]
_OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-2024-08-06",
    "gpt-4o-mini",
    "gpt-3.5-turbo",
]
_GROK_MODELS = [
    "grok-3-mini",
    "grok-2-1212",
]
_DEEPSEEK_MODELS = [
    "deepseek-chat",      # DeepSeek-V3 — general purpose, high quality
    "deepseek-reasoner",  # DeepSeek-R1 — chain-of-thought (fallback)
]

# ── Backoff state (module-level — shared across all agents) ────────────────────



_BACKOFF_SECONDS = [2, 4, 8, 16]

# ── Dynamic provider priority (hot-reloadable) ─────────────────────────────────

_DEFAULT_PRIORITY = ["gemini", "claude", "openai", "deepseek", "grok", "puter"]
_provider_priority: list[str] = list(_DEFAULT_PRIORITY)


def get_provider_priority() -> list[str]:
    return list(_provider_priority)


def set_provider_priority(order: list[str]) -> list[str]:
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
    return {}  # Managed via cache


async def reset_provider_backoff(name: str | None = None) -> dict:
    if name:
        await cache.delete(f"ai_backoff:{name}")
        await cache.delete(f"ai_failures:{name}")
        logger.info("[ai-client] backoff+failures reset for: %s", name)
        return {name: 0.0}
    else:
        await cache.delete_pattern("ai_backoff:*")
        await cache.delete_pattern("ai_failures:*")
        logger.info("[ai-client] backoff+failures reset for all")
        return {}


async def _provider_available(name: str) -> bool:
    until = await cache.get(f"ai_backoff:{name}")
    if until is None:
        return True
    return time.monotonic() >= float(until)


_FATAL_BACKOFF_SECONDS = 300


async def _mark_provider_failed(name: str, status_code: int) -> None:
    fail_data = {
        "status_code": status_code,
        "failed_at": time.time(),
    }
    await cache.set(f"ai_failures:{name}", fail_data, ttl=3600)
    await cache.set(f"ai_backoff:{name}", time.monotonic() + _FATAL_BACKOFF_SECONDS, ttl=_FATAL_BACKOFF_SECONDS)
    logger.warning(
        "[ai-client] %s returned HTTP %d — marked as failing, backing off for %d min",
        name, status_code, _FATAL_BACKOFF_SECONDS // 60,
    )


async def _mark_rate_limited(name: str, retry_after: Optional[str] = None) -> None:
    wait = 8.0
    if retry_after:
        try:
            wait = max(float(retry_after), 4.0)
        except ValueError:
            pass
    await cache.set(f"ai_backoff:{name}", time.monotonic() + wait, ttl=int(wait) + 1)
    logger.warning(f"[ai-client] {name} rate-limited — cooling for {wait:.0f}s")


# ── Provider implementations ───────────────────────────────────────────────────

async def _try_gemini(prompt: str, max_tokens: int, temperature: float) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    if len(api_key) < 20:
        logger.debug("[ai-client] gemini: key too short — skipping (configure a real key to enable)")
        return None
    if not await _provider_available("gemini"):
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
                    await _mark_rate_limited("gemini", resp.headers.get("Retry-After"))
                    return None
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    logger.warning("[ai-client] gemini/%s empty candidates in response", model)
                    continue
                parts = (candidates[0].get("content") or {}).get("parts") or []
                text = parts[0].get("text", "") if parts else ""
                if not text:
                    continue
                logger.debug("[ai-client] gemini/%s responded (%d chars)", model, len(text))
                return text
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            logger.warning("[ai-client] gemini/%s HTTP %d", model, sc)
            if sc in (401, 403):
                await _mark_provider_failed("gemini", sc)
        except Exception as e:
            logger.warning("[ai-client] gemini/%s error: %s", model, e)
    return None


async def _try_claude(prompt: str, max_tokens: int, temperature: float) -> str | None:
    api_key = (
        os.getenv("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
        or os.getenv("CLAUDE_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY", "")
    ).strip()
    if not api_key:
        return None
    if len(api_key) < 20:
        logger.debug("[ai-client] claude: key too short — skipping (configure a real key to enable)")
        return None
    if not await _provider_available("claude"):
        return None

    # Anthropic requires temperature in [0.0, 1.0]
    clamped_temp = max(0.0, min(1.0, temperature))

    url = "https://api.anthropic.com/v1/messages"
    _400_count = 0
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
                        "temperature": clamped_temp,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                if resp.status_code == 404:
                    continue
                if resp.status_code == 400:
                    logger.warning("[ai-client] claude/%s HTTP 400 — skipping model", model)
                    _400_count += 1
                    continue
                if resp.status_code in (401, 403):
                    logger.warning("[ai-client] claude/%s HTTP %d — marking provider failed", model, resp.status_code)
                    await _mark_provider_failed("claude", resp.status_code)
                    return None
                if resp.status_code == 429:
                    await _mark_rate_limited("claude", resp.headers.get("Retry-After"))
                    return None
                if resp.status_code == 529:
                    await _mark_rate_limited("claude", "10")
                    return None
                resp.raise_for_status()
                data = resp.json()
                content_blocks = data.get("content") or []
                text = content_blocks[0].get("text", "") if content_blocks else ""
                if not text:
                    logger.warning("[ai-client] claude/%s empty content in response", model)
                    continue
                logger.debug("[ai-client] claude/%s responded (%d chars)", model, len(text))
                return text
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            logger.warning("[ai-client] claude/%s HTTP %d", model, sc)
            if sc in (401, 403): # Fatal auth/billing
                await _mark_provider_failed("claude", sc)
                return None
        except Exception as e:
            logger.warning("[ai-client] claude/%s error: %s", model, e)

    if _400_count >= len(_CLAUDE_MODELS):
        logger.error("[ai-client] claude exhausted all models with 400 errors")
        await _mark_provider_failed("claude", 400)
    return None


async def _try_openai(prompt: str, max_tokens: int, temperature: float) -> str | None:
    api_key = (os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")).strip()
    if not api_key:
        return None
    if len(api_key) < 10:
        logger.debug("[ai-client] openai: key too short — skipping (configure a real key to enable)")
        return None
    if not await _provider_available("openai"):
        return None

    base_url = os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "").rstrip("/")
    url = f"{base_url}/chat/completions" if base_url else "https://api.openai.com/v1/chat/completions"
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
                    await _mark_rate_limited("openai", resp.headers.get("Retry-After"))
                    return None
                resp.raise_for_status()
                choices = resp.json().get("choices") or []
                text = (choices[0].get("message") or {}).get("content", "") if choices else ""
                if not text:
                    logger.warning("[ai-client] openai/%s empty choices in response", model)
                    continue
                logger.debug("[ai-client] openai/%s responded (%d chars)", model, len(text))
                return text
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            logger.warning("[ai-client] openai/%s HTTP %d", model, sc)
            if sc in (401, 403):
                await _mark_provider_failed("openai", sc)
        except Exception as e:
            logger.warning("[ai-client] openai/%s error: %s", model, e)
    return None


async def _try_grok(prompt: str, max_tokens: int, temperature: float) -> str | None:
    api_key = os.getenv("XAI_API_KEY", "").strip()
    if not api_key:
        return None
    if len(api_key) < 20:
        logger.debug("[ai-client] grok: key too short — skipping (configure a real key to enable)")
        return None
    if not await _provider_available("grok"):
        return None

    url = "https://api.x.ai/v1/chat/completions"
    for model in _GROK_MODELS:
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
                    await _mark_rate_limited("grok", resp.headers.get("Retry-After"))
                    return None
                resp.raise_for_status()
                choices = resp.json().get("choices") or []
                text = (choices[0].get("message") or {}).get("content", "") if choices else ""
                if not text:
                    logger.warning("[ai-client] grok/%s empty choices in response", model)
                    continue
                logger.debug("[ai-client] grok/%s responded (%d chars)", model, len(text))
                return text
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            body = e.response.text[:200]
            logger.warning("[ai-client] grok/%s HTTP %d — %s", model, sc, body)
            if sc in (401, 403): # Fatal auth/billing
                await _mark_provider_failed("grok", sc)
                return None
            if sc == 400:
                continue
        except Exception as e:
            logger.warning("[ai-client] grok/%s error: %s", model, e)
    return None


async def _try_deepseek(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """DeepSeek — OpenAI-compatible API (deepseek.com).

    Uses deepseek-chat (DeepSeek-V3) as the primary model and falls back to
    deepseek-reasoner (R1) which provides chain-of-thought analysis.
    DeepSeek-reasoner uses a fixed temperature of 0.6 per API requirements.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None
    if len(api_key) < 20:
        logger.debug("[ai-client] deepseek: key too short — skipping (configure a real key to enable)")
        return None
    if not await _provider_available("deepseek"):
        return None

    url = "https://api.deepseek.com/v1/chat/completions"
    for model in _DEEPSEEK_MODELS:
        # deepseek-reasoner requires temperature in a narrow range
        model_temp = 0.6 if model == "deepseek-reasoner" else min(temperature, 1.5)
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
                        "temperature": model_temp,
                    },
                )
                if resp.status_code == 404:
                    continue
                if resp.status_code == 429:
                    await _mark_rate_limited("deepseek", resp.headers.get("Retry-After"))
                    return None
                resp.raise_for_status()
                choices = resp.json().get("choices") or []
                text = (choices[0].get("message") or {}).get("content", "") if choices else ""
                if not text:
                    logger.warning("[ai-client] deepseek/%s empty choices in response", model)
                    continue
                logger.debug("[ai-client] deepseek/%s responded (%d chars)", model, len(text))
                return text
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            logger.warning("[ai-client] deepseek/%s HTTP %d", model, sc)
            if sc in (401, 403): # Fatal auth/billing
                await _mark_provider_failed("deepseek", sc)
                return None
            if sc == 400:
                continue
        except Exception as e:
            logger.warning("[ai-client] deepseek/%s error: %s", model, e)
    return None


async def _try_puter(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Puter AI — free tier via puter.com REST API (requires PUTER_API_KEY)."""
    from app.services.puter_ai import try_puter
    if not await _provider_available("puter"):
        return None
    try:
        result = await try_puter(prompt, max_tokens, temperature)
        if result:
            logger.debug("[ai-client] puter responded (%d chars)", len(result))
        return result
    except Exception as e:
        logger.warning("[ai-client] puter error: %s", e)
        return None


# ── Public API ──────────────────────────────────────────────────────────────

async def call_ai_with_provider(
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.2,
    preferred: str | None = None,
) -> tuple[str, str] | None:
    """
    Like call_ai() but returns (text, provider_name) on success, or None on failure.
    """
    _fn_map = {
        "gemini":   _try_gemini,
        "claude":   _try_claude,
        "openai":   _try_openai,
        "deepseek": _try_deepseek,
        "grok":     _try_grok,
        "puter":    _try_puter,
    }
    providers = [(n, _fn_map[n]) for n in _provider_priority if n in _fn_map]
    if preferred and preferred in _fn_map:
        providers.sort(key=lambda p: 0 if p[0] == preferred else 1)

    for name, fn in providers:
        if not await _provider_available(name):
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

    Tries providers in priority order: Gemini → Claude → OpenAI → DeepSeek → Grok → Puter.
    Rate-limited providers are skipped and retried next cycle.
    Returns None if all providers are unavailable or fail.
    """
    _fn_map = {
        "gemini":   _try_gemini,
        "claude":   _try_claude,
        "openai":   _try_openai,
        "deepseek": _try_deepseek,
        "grok":     _try_grok,
        "puter":    _try_puter,
    }
    providers = [(n, _fn_map[n]) for n in _provider_priority if n in _fn_map]

    if preferred and preferred in _fn_map:
        providers.sort(key=lambda p: 0 if p[0] == preferred else 1)

    for name, fn in providers:
        if not await _provider_available(name):
            logger.debug("[ai-client] skipping %s (cooling down)", name)
            continue
        result = await fn(prompt, max_tokens, temperature)
        if result:
            return result

    logger.error("[ai-client] all providers failed or unavailable for prompt (len=%d)", len(prompt))
    return None


async def provider_status() -> dict[str, dict]:
    """Return granular availability status of all providers.

    Status levels:
      - 🟢 available: configured, not cooling, not failing
      - 🟡 cooling: rate-limited or recovering from error
      - 🔴 failing: fatal auth error (401/403) — backed off for 30 min
      - ⚫ not_configured: API key missing or too short
    """
    from app.services.puter_ai import puter_status
    now = time.monotonic()

    def _key_valid(env_var: str, min_len: int = 10) -> bool:
        v = os.getenv(env_var, "").strip()
        return len(v) >= min_len

    def _any_key_valid(*env_vars: str, min_len: int = 10) -> bool:
        return any(len(os.getenv(v, "").strip()) >= min_len for v in env_vars)

    keys = {
        "gemini":   _any_key_valid("GEMINI_API_KEY",                              min_len=20),
        "claude":   _any_key_valid("CLAUDE_API_KEY", "ANTHROPIC_API_KEY",         min_len=20),
        "openai":   _any_key_valid("AI_INTEGRATIONS_OPENAI_API_KEY", "OPENAI_API_KEY"),
        "deepseek": _any_key_valid("DEEPSEEK_API_KEY",                            min_len=20),
        "grok":     _any_key_valid("XAI_API_KEY",                                 min_len=20),
    }

    result = {}
    for name, has_key in keys.items():
        cooling_until = await cache.get(f"ai_backoff:{name}") or 0.0
        cooling = cooling_until > now
        failure = await cache.get(f"ai_failures:{name}")


        # Determine status
        if not has_key:
            status = "not_configured"
        elif failure:
            status = "failing"
        elif cooling:
            status = "cooling"
        else:
            status = "available"

        result[name] = {
            "status": status,
            "configured": has_key,
            "available": has_key and not cooling and not failure,
            "cooling": cooling,
            "cooling_for_seconds": max(0, round(cooling_until - now, 1)) if cooling else 0,
            "failing": bool(failure),
            "last_error_code": failure["status_code"] if failure else None,
            "last_error_time": failure["failed_at"] if failure else None,
        }

    result["puter"] = puter_status()
    return result


async def verify_provider(name: str) -> bool:
    """F20: Active health probe for AI providers.

    Performs a minimal 'Hello' call to verify API key validity.
    """
    prompt = "Hello. Reply with 'ok' and nothing else."
    try:
        if name == "gemini":
            return await _try_gemini(prompt, 5, 0.1) is not None
        if name == "claude":
            return await _try_claude(prompt, 5, 0.1) is not None
        if name == "openai":
            return await _try_openai(prompt, 5, 0.1) is not None
        if name == "deepseek":
            return await _try_deepseek(prompt, 5, 0.1) is not None
        if name == "grok":
            return await _try_grok(prompt, 5, 0.1) is not None
        return False
    except Exception:
        return False
