"""app/agents/kyc_screener_agent.py  — Item 1: KYC Auto-Screener

Runs every 10 minutes. Finds pending KYC submissions, calls Gemini to
validate the submitted identity data fields, then auto-approves clean
submissions, auto-rejects clearly invalid ones, and escalates uncertain
cases to the admin queue with an AI-generated risk summary.

Auto-approve criteria (all must pass):
  - full_name present and plausible (2+ words)
  - document_type recognised
  - document_number present and length-valid
  - dob present
  - Gemini confidence >= 0.75

Auto-reject criteria (any triggers):
  - critical fields missing
  - document_number appears fake/random
  - Gemini flags the submission as suspicious
  - Gemini confidence < 0.40

Otherwise → status set to 'manual_review' with AI note attached.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List


from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

MAX_PER_CYCLE = 10



def _build_kyc_prompt(kyc_data: dict, user_email: str) -> str:
    return (
        f"You are a KYC compliance officer. Assess this identity submission.\n\n"
        f"Email: {user_email}\n"
        f"Submitted data: {json.dumps(kyc_data, indent=2)}\n\n"
        f"Return ONLY this JSON (no markdown):\n"
        f'{{\n'
        f'  "verdict": "approve"|"reject"|"manual_review",\n'
        f'  "confidence": 0.00,\n'
        f'  "reason": "one-line explanation",\n'
        f'  "risk_flags": ["flag1"]\n'
        f'}}\n\n'
        f"Approve if: full_name has 2+ words, document_type is standard (passport/drivers_license/national_id), "
        f"document_number is plausible length (6-20 chars), dob present.\n"
        f"Reject if: critical fields missing, document_number looks fake (all same digit, sequential, or <4 chars).\n"
        f"manual_review if: borderline or unusual."
    )


class KYCScreenerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="kyc-screener",
            interval_seconds=10 * 60,
            initial_delay_seconds=30,
        )

    async def run_cycle(self) -> Dict[str, Any]:

        from app.db.database import AsyncSessionLocal
        from app.db.models import User
        from sqlalchemy import select

        approved = rejected = escalated = 0
        processed_ids: List[int] = []

        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(User)
                .where(User.kyc_status == "pending")
                .limit(MAX_PER_CYCLE)
            )
            users = res.scalars().all()

            for user in users:
                kyc_data = getattr(user, "kyc_data", None) or {}
                email = getattr(user, "email", "unknown")

                prompt = _build_kyc_prompt(kyc_data, email)
                raw = await call_ai(prompt)

                verdict = "manual_review"
                reason = "AI review inconclusive"
                confidence = 0.5

                if raw:
                    try:
                        text = raw.strip()
                        obj_match = __import__("re").search(r"\{[\s\S]*\}", text)
                        if obj_match:
                            parsed = json.loads(obj_match.group())
                            verdict = parsed.get("verdict", "manual_review")
                            reason = parsed.get("reason", "")
                            confidence = float(parsed.get("confidence", 0.5))
                    except Exception:
                        pass

                if verdict == "approve" and confidence >= 0.75:
                    user.kyc_status = "approved"
                    user.kyc_verified = True
                    approved += 1
                    logger.info(
                        "[kyc-screener] AUTO-APPROVED user=%d conf=%.2f reason=%s",
                        user.id, confidence, reason,
                    )
                elif verdict == "reject" or confidence < 0.40:
                    user.kyc_status = "rejected"
                    user.kyc_verified = False
                    rejected += 1
                    logger.info(
                        "[kyc-screener] AUTO-REJECTED user=%d conf=%.2f reason=%s",
                        user.id, confidence, reason,
                    )
                else:
                    user.kyc_status = "manual_review"
                    # Store AI note in kyc_data
                    kyc_data["_ai_note"] = reason
                    kyc_data["_ai_confidence"] = confidence
                    user.kyc_data = kyc_data
                    escalated += 1
                    logger.info(
                        "[kyc-screener] ESCALATED user=%d conf=%.2f reason=%s",
                        user.id, confidence, reason,
                    )

                processed_ids.append(user.id)
                await asyncio.sleep(1.5)

            if processed_ids:
                await db.commit()

        result = {
            "processed": len(processed_ids),
            "approved": approved,
            "rejected": rejected,
            "escalated": escalated,
        }
        logger.info("[kyc-screener] cycle: %s", result)
        return result
