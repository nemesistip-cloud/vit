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
    return ChatResponse(**result)


@router.get("/status")
async def assistant_status(_user=Depends(verify_api_key)):
    """Report whether the assistant is available (i.e. key is configured)."""
    import os
    configured = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {
        "available": configured,
        "provider": "gemini-1.5-flash",
        "message": (
            "Assistant ready." if configured
            else "Add a GEMINI_API_KEY in Admin → API Keys to enable the assistant."
        ),
    }
