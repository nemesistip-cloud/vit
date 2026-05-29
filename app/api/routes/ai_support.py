"""app/api/routes/ai_support.py  — Item 7: AI Customer Support Agent

Provides a data-aware AI support endpoint that answers user questions
about their own account — predictions, withdrawals, trust score, KYC
status, subscription — using Gemini with real DB context injected.

POST /api/support/chat
  { "question": "Why is my withdrawal pending?" }

Returns:
  { "answer": "...", "context_used": [...] }

Rate limiting: max 10 questions per user per hour (in-memory).
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User, Prediction, AIPrediction
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/support", tags=["ai-support"])

# In-memory rate limit: {user_id: [timestamp, ...]}
# Note: resets on restart — acceptable for support throttling (10 q/hour per user)
_RATE_LIMIT: dict[int, list[float]] = defaultdict(list)
RATE_LIMIT_PER_HOUR = 10


class SupportChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


async def _gather_user_context(db: AsyncSession, user: User) -> dict:
    """Load the user's key account data to inject into the AI prompt."""
    ctx: dict = {}

    # Basic account info
    ctx["email"] = getattr(user, "email", "")
    ctx["role"] = getattr(user, "role", "user")
    ctx["subscription_tier"] = getattr(user, "subscription_tier", "viewer")
    ctx["kyc_status"] = getattr(user, "kyc_status", "none")
    ctx["kyc_verified"] = getattr(user, "kyc_verified", False)
    ctx["account_created"] = (
        user.created_at.strftime("%Y-%m-%d") if getattr(user, "created_at", None) else "unknown"
    )

    # Trust score
    try:
        from app.modules.trust.models import UserTrustScore
        ts_res = await db.execute(
            select(UserTrustScore).where(UserTrustScore.user_id == user.id)
        )
        ts = ts_res.scalar_one_or_none()
        if ts:
            ctx["trust_score"] = round(ts.composite_score, 1)
            ctx["risk_tier"] = ts.risk_tier
    except Exception:
        pass

    # Wallet
    try:
        from app.modules.wallet.models import Wallet, WithdrawalRequest
        w_res = await db.execute(
            select(Wallet).where(Wallet.user_id == user.id)
        )
        wallet = w_res.scalar_one_or_none()
        if wallet:
            ctx["wallet_ngn"] = float(wallet.ngn_balance or 0)
            ctx["wallet_usd"] = float(wallet.usd_balance or 0)
            ctx["wallet_vitcoin"] = float(wallet.vitcoin_balance or 0)

        # Recent withdrawals
        wd_res = await db.execute(
            select(WithdrawalRequest)
            .where(WithdrawalRequest.user_id == user.id)
            .order_by(WithdrawalRequest.requested_at.desc())
            .limit(3)
        )
        wds = wd_res.scalars().all()
        ctx["recent_withdrawals"] = [
            {
                "amount": float(r.amount or 0),
                "currency": r.currency,
                "status": r.status,
                "review_note": r.review_note or "",
                "requested": r.requested_at.strftime("%Y-%m-%d") if r.requested_at else "",
            }
            for r in wds
        ]
    except Exception:
        pass

    # Recent predictions
    try:
        pred_res = await db.execute(
            select(Prediction)
            .where(Prediction.user_id == user.id)
            .order_by(Prediction.created_at.desc())
            .limit(5)
        )
        preds = pred_res.scalars().all()
        ctx["recent_predictions"] = len(preds)
    except Exception:
        pass

    # Open fraud flags count
    try:
        from app.modules.trust.models import FraudFlag
        from sqlalchemy import func
        flag_count = (await db.execute(
            select(func.count(FraudFlag.id))
            .where(FraudFlag.user_id == user.id, FraudFlag.status == "open")
        )).scalar() or 0
        ctx["open_fraud_flags"] = flag_count
    except Exception:
        pass

    return ctx


def _build_support_prompt(question: str, user_context: dict) -> str:
    import json
    ctx_str = json.dumps(user_context, indent=2, default=str)
    return (
        f"You are the AI support agent for VIT Sports Intelligence Network.\n"
        f"Answer the user's question using ONLY the provided account context — "
        f"do not make up information not present in the context.\n"
        f"Be helpful, concise, and empathetic. If you cannot answer from the context, "
        f"say so clearly and suggest contacting the admin team.\n\n"
        f"User Account Context:\n{ctx_str}\n\n"
        f"User Question: {question}\n\n"
        f"Answer (max 200 words):"
    )


def _check_rate_limit(user_id: int) -> bool:
    now = time.time()
    hour_ago = now - 3600
    calls = _RATE_LIMIT[user_id]
    # Prune old calls
    _RATE_LIMIT[user_id] = [t for t in calls if t > hour_ago]
    if len(_RATE_LIMIT[user_id]) >= RATE_LIMIT_PER_HOUR:
        return False
    _RATE_LIMIT[user_id].append(now)
    return True


@router.post("/chat")
async def support_chat(
    body: SupportChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI-powered support chat with full user context awareness.

    Uses the shared AI cascade (Gemini → Claude → OpenAI → Grok) so the
    endpoint keeps working even when a single provider is down or rate-limited.
    """
    if not _check_rate_limit(user.id):
        raise HTTPException(429, f"Rate limit: max {RATE_LIMIT_PER_HOUR} support questions per hour")

    user_ctx = await _gather_user_context(db, user)
    prompt = _build_support_prompt(body.question, user_ctx)
    answer = await call_ai(prompt, max_tokens=500, temperature=0.4)

    if not answer:
        raise HTTPException(503, "AI support is temporarily unavailable — please try again shortly")

    logger.info("[ai-support] answered question for user=%d", user.id)
    return {
        "answer": answer,
        "context_fields": list(user_ctx.keys()),
    }


@router.get("/status")
async def support_status(user: User = Depends(get_current_user)):
    """Check AI support availability and per-user usage."""
    from app.services.ai_client import provider_status
    now = time.time()
    calls_this_hour = len([t for t in _RATE_LIMIT.get(user.id, []) if t > now - 3600])
    providers = await provider_status()
    ai_available = any(p["available"] for p in providers.values())
    return {
        "available": ai_available,
        "calls_used": calls_this_hour,
        "calls_remaining": max(0, RATE_LIMIT_PER_HOUR - calls_this_hour),
        "rate_limit_per_hour": RATE_LIMIT_PER_HOUR,
        "providers": {k: v["available"] for k, v in providers.items()},
    }
