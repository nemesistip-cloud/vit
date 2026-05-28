"""app/api/routes/ai_assistant.py — In-app AI Assistant chat endpoint."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.middleware.auth import verify_api_key
from app.core.errors import AppError
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
    thoughts: List[str] = Field(default_factory=list, description="Chain of thought traces")


@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(
    body: ChatRequest,
    _user=Depends(verify_api_key),
):
    """Send a message to the AI Assistant and receive a reply."""
    if not body.message.strip():
        raise AppError("Message cannot be empty", status_code=422, code="invalid_message")

    history_dicts = [t.model_dump() for t in (body.history or [])]
    result = await gemini_chat(
        message=body.message,
        history=history_dicts,
        context=body.context,
    )
    return ChatResponse(**result)


@router.get("/status")
async def assistant_status(_user=Depends(verify_api_key)):
    """Report whether the assistant is available and which provider is configured."""
    import os
    gemini_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
    claude_key  = bool(
        os.getenv("CLAUDE_API_KEY", "").strip()
        or os.getenv("ANTHROPIC_API_KEY", "").strip()
    )
    configured_providers = []
    if gemini_key:
        configured_providers.append("gemini")
    if claude_key:
        configured_providers.append("claude")

    backend_available = len(configured_providers) > 0
    provider = "gemini-1.5-flash" if gemini_key else ("claude-3-haiku" if claude_key else "puter-claude")

    return {
        "available": backend_available or True,
        "backend_ai_available": backend_available,
        "configured_providers": configured_providers,
        "provider": provider,
        "puter_available": True,
        "message": (
            "Assistant ready." if backend_available
            else "Assistant is available through Puter. Configure GEMINI_API_KEY or CLAUDE_API_KEY for backend chat support."
        ),
    }
