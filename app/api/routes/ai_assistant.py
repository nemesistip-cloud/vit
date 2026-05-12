"""app/api/routes/ai_assistant.py — In-app AI Assistant chat endpoint.

Provides a conversational interface backed by Gemini that any logged-in user
can use to ask questions about the platform, fixtures, predictions, etc.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.middleware.auth import verify_api_key
from app.services.gemini_chat import chat as gemini_chat

router = APIRouter(prefix="/ai/assistant", tags=["ai-assistant"])


class ChatTurn(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: Optional[List[ChatTurn]] = Field(default=None, description="Prior conversation turns")
    context: Optional[str] = Field(default=None, description="Optional context (e.g. current page)")


class ChatResponse(BaseModel):
    available: bool
    reply: str
    error: Optional[str] = None
    provider: Optional[str] = None
    scie_fallback: bool = False


@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(
    body: ChatRequest,
    _user=Depends(verify_api_key),
):
    """Send a message to the AI Assistant and receive a reply."""
    if not body.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    history_dicts = [t.model_dump() for t in (body.history or [])]
    result = await gemini_chat(
        message=body.message,
        history=history_dicts,
        context=body.context,
    )
    return ChatResponse(
        available=result.get("available", True),
        reply=result.get("reply", ""),
        error=result.get("error"),
        provider=result.get("provider"),
        scie_fallback=result.get("scie_fallback", False),
    )


@router.get("/status")
async def assistant_status(_user=Depends(verify_api_key)):
    """Report whether the assistant is available.

    Always returns available=True — even without API keys, Puter.js (free
    browser-side Claude) is the fallback, so the chat UI is always functional.
    """
    import os
    gemini_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
    claude_key  = bool(
        os.getenv("CLAUDE_API_KEY", "").strip()
        or os.getenv("ANTHROPIC_API_KEY", "").strip()
    )
    grok_key = bool(os.getenv("XAI_API_KEY", "").strip())
    server_configured = gemini_key or claude_key or grok_key

    if gemini_key:
        provider = "Gemini"
        mode = "server"
    elif claude_key:
        provider = "Claude"
        mode = "server"
    elif grok_key:
        provider = "Grok"
        mode = "server"
    else:
        provider = "Puter (free browser-side Claude)"
        mode = "puter"

    return {
        "available": True,
        "server_configured": server_configured,
        "provider": provider,
        "mode": mode,
        "puter_available": True,
        "message": (
            f"Assistant ready via {provider}." if server_configured
            else "Assistant ready via Puter.js (free Claude — no API key needed). Add GEMINI_API_KEY for faster server-side responses."
        ),
    }
