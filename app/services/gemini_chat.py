"""app/services/gemini_chat.py — Conversational Gemini wrapper for the in-app AI Assistant."""

import logging
import os
import json
from typing import List, Dict, Optional, Any

import httpx
import app.services.assistant_tools as assistant_tools
from app.services.assistant_tools import GEMINI_TOOLS, TOOL_MAP

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_CHAT_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]

SYSTEM_PROMPT = (
    "You are VIT Assistant, the in-app sports-betting copilot for the VIT Sports "
    "Intelligence Network. You have access to real-time tools to fetch live data."
    "\n\n"
    "GUIDELINES:\n"
    "1. Use tools whenever a user asks about upcoming matches, live scores, real-time odds, "
    "specific match insights, system health (agent status), or market trends.\n"
    "2. If you use a tool, explain what you found in a helpful, conversational way.\n"
    "3. Never guarantee outcomes. Betting carries risk.\n"
    "4. Keep responses concise and actionable."
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
        "thoughts": []
    }


def _build_contents(history: List[Dict[str, str]], message: str) -> List[Dict]:
    contents: List[Dict] = []
    for turn in history[-12:]:
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
    """Send a chat turn to Gemini with tool-calling support."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _no_key_response()

    if not message or not message.strip():
        return {"available": True, "reply": "Please enter a question.", "error": None, "thoughts": []}

    system_text = SYSTEM_PROMPT
    if context:
        system_text += f"\n\nAdditional context for this conversation:\n{context.strip()}"

    contents = _build_contents(history or [], message)
    thoughts = []

    payload = {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "tools": GEMINI_TOOLS,
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1000,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Initial request to model
            model = _GEMINI_CHAT_MODELS[0]
            url = f"{_GEMINI_BASE}/{model}:generateContent?key={api_key}"

            resp = await client.post(url, json=payload)
            if not resp.is_success:
                return {"available": False, "reply": "Model error.", "error": f"HTTP {resp.status_code}", "thoughts": []}

            data = resp.json()
            candidate = data.get("candidates", [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            # 2. Tool calling loop (up to 3 iterations)
            for _ in range(3):
                tool_calls = [p.get("functionCall") for p in parts if p.get("functionCall")]

                if not tool_calls:
                    break

                # Model wants to use tools
                tool_responses = []
                # Important: Model expect we send back EXACTLY the same content it sent us
                # that contains the functionCall parts, then a role: "function" content.
                # However, Gemini v1beta actually expects role: "model" for the functionCall
                # and role: "function" for the response.

                for tc in tool_calls:
                    fn_name = tc.get("name")
                    args = tc.get("args", {})

                    thought = f"Executing {fn_name}({json.dumps(args)})..."
                    thoughts.append(thought)
                    logger.info(f"[gemini-chat] {thought}")

                    if fn_name in TOOL_MAP:
                        try:
                            tool_callable = getattr(assistant_tools, fn_name, TOOL_MAP[fn_name])
                            result = await tool_callable(**args)
                            tool_responses.append({
                                "functionResponse": {
                                    "name": fn_name,
                                    "response": {"name": fn_name, "content": result}
                                }
                            })
                        except Exception as e:
                            tool_responses.append({
                                "functionResponse": {
                                    "name": fn_name,
                                    "response": {"name": fn_name, "content": {"error": str(e)}}
                                }
                            })
                    else:
                        tool_responses.append({
                            "functionResponse": {
                                "name": fn_name,
                                "response": {"name": fn_name, "content": {"error": "Tool not found"}}
                            }
                        })

                # Append tool call and its response to conversation history
                # Ensure the model's turn is correctly typed
                model_turn = {"role": "model", "parts": content.get("parts")}
                contents.append(model_turn)
                contents.append({"role": "function", "parts": tool_responses})

                # Send back to Gemini
                payload["contents"] = contents
                resp = await client.post(url, json=payload)
                if not resp.is_success:
                    logger.error(f"[gemini-chat] tool loop error: {resp.status_code} {resp.text}")
                    break

                data = resp.json()
                candidate = data.get("candidates", [{}])[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])

            # 3. Final response assembly
            reply_text = "".join(p.get("text", "") for p in parts if p.get("text", "")).strip()
            if not reply_text:
                if any(p.get("functionCall") for p in parts):
                    reply_text = "I've processed the data but didn't summarize it. Ask me to explain it!"
                else:
                    reply_text = "The model didn't produce a text response."

            return {
                "available": True,
                "reply": reply_text,
                "error": None,
                "thoughts": thoughts
            }

    except Exception as exc:
        logger.error(f"Gemini agent error: {exc}")
        return {
            "available": False,
            "reply": "Assistant encountered an error.",
            "error": str(exc),
            "thoughts": thoughts
        }
