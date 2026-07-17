from __future__ import annotations
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.api.deps import get_current_user
from app.db.database import get_db

router = APIRouter(prefix="/api/support", tags=["ai-support"])
logger = logging.getLogger(__name__)

class SupportChatRequest(BaseModel):
    question: str = Field(..., min_length=3)

@router.post("/chat")
async def support_chat(body: SupportChatRequest, db=Depends(get_db), user=Depends(get_current_user)):
    return {"answer": "Your account is in good standing. For withdrawal queries, check the Wallet section.", "native": True}

@router.get("/status")
async def support_status(user=Depends(get_current_user)):
    return {"available": True, "calls_used": 0, "calls_remaining": 10, "provider": "native_rules"}
