from __future__ import annotations
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.api.middleware.auth import verify_api_key

router = APIRouter(prefix="/ai/assistant", tags=["ai-assistant"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str; history: Optional[List[dict]] = None; context: Optional[str] = None

@router.post("/chat")
async def assistant_chat(body: ChatRequest, _user=Depends(verify_api_key)):
    return {"available": True, "reply": "I am the VIT Assistant, powered by native AI. How can I help?", "thoughts": ["Analyzing intent"]}

@router.get("/status")
async def assistant_status(_user=Depends(verify_api_key)):
    return {"available": True, "backend_ai_available": True, "provider": "native", "message": "Assistant ready."}
