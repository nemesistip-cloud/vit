"""app/services/gemini_chat.py — Conversational Gemini wrapper for the in-app AI Assistant."""

import logging
import os
from typing import List, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

GEMINI_CHAT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/gemini-1.5-flash:generateContent"
)

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


def _no_key_response() -> Dict:
    return {
        "available": False,
        "reply": (
            "The AI Assistant is not configured yet. An admin needs to add a "
            "GEMINI_API_KEY in **Admin → API Keys** to enable conversational "
            "responses."
        ),
        "error": "GEMINI_API_KEY not configured",
    }


def _build_contents(history: List[Dict[str, str]], message: str) -> List[Dict]:
    """Convert chat history + new user message into Gemini's `contents` format.

    Each history item is {role: "user"|"assistant", content: "..."}.
    Gemini expects role values "user" and "model".
    """
    contents: List[Dict] = []
    for turn in history[-12:]:  # cap context window
        role = "user" if turn.get("role") == "user" else "model"
        text = (turn.get("content") or "").strip()
        if not text:
            continue
        contents.append({"role": role, "parts": [{"text": text}]})

    contents.append({"role": "user", "parts": [{"text": message.strip()}]})
    return contents


async def chat(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    context: Optional[str] = None,
) -> Dict:
    """Send a chat turn to Gemini and return the assistant reply.

    Args:
        message: the new user message.
        history: prior conversation [{role, content}, ...] (optional).
        context: extra system context to inject (e.g., current page or match).

    Returns:
        {"available": bool, "reply": str, "error": str|None}
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _no_key_response()

    if not message or not message.strip():
        return {"available": True, "reply": "Please enter a question.", "error": None}

    system_text = SYSTEM_PROMPT
    if context:
        system_text += f"\n\nAdditional context for this conversation:\n{context.strip()}"

    payload = {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": _build_contents(history or [], message),
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 800,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post(
                f"{GEMINI_CHAT_URL}?key={api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        if resp.status_code in (401, 403):
            return {
                "available": False,
                "reply": "The configured Gemini API key was rejected. Please update it in Admin → API Keys.",
                "error": "Invalid Gemini API key",
            }
        if resp.status_code == 429:
            return {
                "available": False,
                "reply": "The AI Assistant is rate-limited right now. Please try again in a few seconds.",
                "error": "Rate limit reached",
            }
        if not resp.is_success:
            return {
                "available": False,
                "reply": f"Gemini returned an error (HTTP {resp.status_code}). Please try again later.",
                "error": f"HTTP {resp.status_code}",
            }

        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return {
                "available": True,
                "reply": "The model didn't produce a response. Try rephrasing your question.",
                "error": None,
            }

        parts = candidates[0].get("content", {}).get("parts", [])
        reply_text = "".join(p.get("text", "") for p in parts).strip()
        if not reply_text:
            reply_text = "The model didn't produce a response. Try rephrasing your question."

        return {"available": True, "reply": reply_text, "error": None}

    except httpx.TimeoutException:
        return {
            "available": False,
            "reply": "The AI Assistant timed out. Please try a shorter question or try again.",
            "error": "Timeout",
        }
    except Exception as exc:
        logger.error(f"Gemini chat error: {exc}")
        return {
            "available": False,
            "reply": "Something went wrong talking to the AI Assistant. Please try again.",
            "error": str(exc),
        }
