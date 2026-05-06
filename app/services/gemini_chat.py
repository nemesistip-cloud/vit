"""app/services/gemini_chat.py — Multi-provider AI chat with Gemini→Claude→Grok cascade."""

import logging
import os
from typing import List, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_CHAT_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]

_CLAUDE_BASE  = "https://api.anthropic.com/v1/messages"
_CLAUDE_MODEL = "claude-3-5-haiku-20241022"

_GROK_BASE  = "https://api.x.ai/v1/chat/completions"
_GROK_MODEL = "grok-2-1212"

SYSTEM_PROMPT = (
    "You are VIT Assistant, the in-app sports-betting copilot for the VIT Sports "
    "Intelligence Network. You help users understand the platform's features "
    "(predictions, ML models, ROI/CLV analytics, the accumulator builder, the "
    "trust system, the validator network, governance, the wallet, training "
    "pipeline, AI insights, KYC, subscriptions and the developer API), reason "
    "about football fixtures, and interpret model output. Always stay grounded "
    "in the data you are given; if a question requires live data you do not "
    "have, say so. Keep responses concise, conversational, and actionable. "
    "Never give guarantees about bet outcomes or financial advice; remind users "
    "that betting carries risk."
)


def _build_gemini_contents(history: List[Dict[str, str]], message: str) -> List[Dict]:
    """Convert chat history + new message into Gemini contents format."""
    contents: List[Dict] = []
    for turn in history[-12:]:
        role = "user" if turn.get("role") == "user" else "model"
        text = (turn.get("content") or "").strip()
        if not text:
            continue
        contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": message.strip()}]})
    return contents


def _build_openai_messages(history: List[Dict[str, str]], message: str, system_text: str) -> List[Dict]:
    msgs: List[Dict] = [{"role": "system", "content": system_text}]
    for turn in history[-12:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        text = (turn.get("content") or "").strip()
        if text:
            msgs.append({"role": role, "content": text})
    msgs.append({"role": "user", "content": message.strip()})
    return msgs


async def _try_gemini(
    client: httpx.AsyncClient,
    api_key: str,
    system_text: str,
    history: List[Dict],
    message: str,
) -> Optional[Dict]:
    payload = {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": _build_gemini_contents(history, message),
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 800},
    }
    resp = None
    for model in _GEMINI_CHAT_MODELS:
        url = f"{_GEMINI_BASE}/{model}:generateContent?key={api_key}"
        try:
            resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        except httpx.TimeoutException:
            logger.debug("[chat-cascade] gemini/%s timed out", model)
            continue
        if resp.status_code not in (404, 503):
            break
        logger.debug("[chat-cascade] gemini/%s unavailable (%s), trying next", model, resp.status_code)

    if resp is None:
        return None
    if resp.status_code in (401, 403):
        logger.warning("[chat-cascade] Gemini auth error %s", resp.status_code)
        return None
    if resp.status_code == 429:
        logger.warning("[chat-cascade] Gemini rate-limited — cascading to Claude")
        return None
    if not resp.is_success:
        logger.warning("[chat-cascade] Gemini HTTP %s — cascading", resp.status_code)
        return None

    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return None
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        return None
    return {"available": True, "reply": text, "error": None, "provider": "gemini"}


async def _try_claude(
    client: httpx.AsyncClient,
    api_key: str,
    system_text: str,
    history: List[Dict],
    message: str,
) -> Optional[Dict]:
    if not api_key:
        return None

    msgs = []
    for turn in history[-12:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        text = (turn.get("content") or "").strip()
        if text:
            msgs.append({"role": role, "content": text})
    msgs.append({"role": "user", "content": message.strip()})

    payload = {
        "model": _CLAUDE_MODEL,
        "max_tokens": 800,
        "system": system_text,
        "messages": msgs,
    }
    try:
        resp = await client.post(
            _CLAUDE_BASE,
            json=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
    except httpx.TimeoutException:
        logger.warning("[chat-cascade] Claude timed out — cascading to Grok")
        return None

    if resp.status_code == 429:
        logger.warning("[chat-cascade] Claude rate-limited — cascading to Grok")
        return None
    if not resp.is_success:
        logger.warning("[chat-cascade] Claude HTTP %s — cascading", resp.status_code)
        return None

    data = resp.json()
    content_blocks = data.get("content") or []
    text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text").strip()
    if not text:
        return None
    return {"available": True, "reply": text, "error": None, "provider": "claude"}


async def _try_grok(
    client: httpx.AsyncClient,
    api_key: str,
    system_text: str,
    history: List[Dict],
    message: str,
) -> Optional[Dict]:
    if not api_key:
        return None

    payload = {
        "model": _GROK_MODEL,
        "max_tokens": 800,
        "temperature": 0.5,
        "messages": _build_openai_messages(history, message, system_text),
    }
    try:
        resp = await client.post(
            _GROK_BASE,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
    except httpx.TimeoutException:
        logger.warning("[chat-cascade] Grok timed out — all providers exhausted")
        return None

    if resp.status_code == 429:
        logger.warning("[chat-cascade] Grok rate-limited — all providers exhausted")
        return None
    if not resp.is_success:
        logger.warning("[chat-cascade] Grok HTTP %s", resp.status_code)
        return None

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return None
    text = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        return None
    return {"available": True, "reply": text, "error": None, "provider": "grok"}


async def chat(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    context: Optional[str] = None,
) -> Dict:
    """Send a chat turn through the cascade: Gemini → Claude → Grok → error.

    Returns:
        {"available": bool, "reply": str, "error": str|None, "provider": str|None}
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    claude_key = os.getenv("CLAUDE_API_KEY", "").strip()
    grok_key   = os.getenv("XAI_API_KEY", "").strip()

    if not any([gemini_key, claude_key, grok_key]):
        return {
            "available": False,
            "reply": (
                "The AI Assistant is not configured yet. An admin needs to add "
                "GEMINI_API_KEY, CLAUDE_API_KEY, or XAI_API_KEY in Admin → API Keys "
                "to enable conversational responses."
            ),
            "error": "No AI provider API key configured",
            "provider": None,
        }

    if not message or not message.strip():
        return {"available": True, "reply": "Please enter a question.", "error": None, "provider": None}

    system_text = SYSTEM_PROMPT
    if context:
        system_text += f"\n\nAdditional context for this conversation:\n{context.strip()}"

    history = history or []

    try:
        async with httpx.AsyncClient(timeout=22) as client:
            if gemini_key:
                result = await _try_gemini(client, gemini_key, system_text, history, message)
                if result:
                    logger.info("[chat-cascade] Served by Gemini")
                    return result

            if claude_key:
                result = await _try_claude(client, claude_key, system_text, history, message)
                if result:
                    logger.info("[chat-cascade] Served by Claude")
                    return result

            if grok_key:
                result = await _try_grok(client, grok_key, system_text, history, message)
                if result:
                    logger.info("[chat-cascade] Served by Grok")
                    return result

        return {
            "available": False,
            "reply": (
                "All AI providers are currently unavailable or rate-limited. "
                "Please try again in a few seconds."
            ),
            "error": "All providers failed",
            "provider": None,
        }

    except Exception as exc:
        logger.error("[chat-cascade] Unhandled error: %s", exc)
        return {
            "available": False,
            "reply": "Something went wrong with the AI Assistant. Please try again.",
            "error": str(exc),
            "provider": None,
        }
