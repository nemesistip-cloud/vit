"""app/agents/withdrawal_gatekeeper_agent.py  — Item 3: Withdrawal Auto-Approval

Runs every 5 minutes. Checks all pending WithdrawalRequests and applies
a rule cascade to auto-approve safe requests or route risky ones to
manual_review.

Auto-approve rule cascade (ALL must pass):
  1. KYC verified on user account
  2. Trust score >= 60 (low risk tier)
  3. No open CRITICAL or HIGH fraud flags
  4. Withdrawal amount within daily tier limit:
       - Free tier:     USD 100  / NGN 150,000
       - Analyst/Pro:   USD 500  / NGN 750,000
       - Elite/Admin:   unlimited
  5. Not more than 2 withdrawals in the last 24 hours

Manual review triggers (any):
  - KYC not verified
  - Trust score < 60
  - Open HIGH/CRITICAL fraud flags
  - Amount exceeds tier limit
  - More than 2 withdrawals in last 24 hours
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

MAX_PER_CYCLE = 20

TIER_LIMITS_USD = {
    "free":     Decimal("100"),
    "viewer":   Decimal("100"),
    "analyst":  Decimal("500"),
    "pro":      Decimal("500"),
    "elite":    Decimal("999999"),
    "admin":    Decimal("999999"),
}
TIER_LIMITS_NGN = {
    "free":     Decimal("150000"),
    "viewer":   Decimal("150000"),
    "analyst":  Decimal("750000"),
    "pro":      Decimal("750000"),
    "elite":    Decimal("999999999"),
    "admin":    Decimal("999999999"),
}


class WithdrawalGatekeeperAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="withdrawal-gatekeeper",
            interval_seconds=5 * 60,
            initial_delay_seconds=20,
        )

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.db.models import User
        from app.modules.wallet.models import WithdrawalRequest
        from app.modules.trust.models import FraudFlag, UserTrustScore
        from app.services.alerts import TelegramAlert, AlertPriority
        from sqlalchemy import select, func

        approved = manual = 0
        now = datetime.now(timezone.utc)
        window_24h = now - timedelta(hours=24)

        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(WithdrawalRequest)
                .where(WithdrawalRequest.status == "pending")
                .order_by(WithdrawalRequest.requested_at.asc())
                .limit(MAX_PER_CYCLE)
            )
            requests = res.scalars().all()

            for req in requests:
                reasons = []

                # ── 1. Load user ──────────────────────────────────────────
                user_res = await db.execute(
                    select(User).where(User.id == req.user_id)
                )
                user = user_res.scalar_one_or_none()
                if not user:
                    req.status = "rejected"
                    req.review_note = "User account not found"
                    continue

                tier = (getattr(user, "subscription_tier", "free") or "free").lower()
                role = (getattr(user, "role", "user") or "user").lower()
                effective_tier = "admin" if role == "admin" else tier

                # ── 2. KYC check ──────────────────────────────────────────
                if not getattr(user, "kyc_verified", False):
                    reasons.append("KYC not verified")

                # ── 3. Trust score ────────────────────────────────────────
                score_res = await db.execute(
                    select(UserTrustScore).where(UserTrustScore.user_id == req.user_id)
                )
                trust = score_res.scalar_one_or_none()
                trust_score = trust.composite_score if trust else 50.0
                if trust_score < 60.0:
                    reasons.append(f"Trust score too low ({trust_score:.0f}/100)")

                # ── 4. Open high/critical fraud flags ─────────────────────
                flag_count = (await db.execute(
                    select(func.count(FraudFlag.id)).where(
                        FraudFlag.user_id == req.user_id,
                        FraudFlag.status == "open",
                        FraudFlag.severity.in_(["high", "critical"]),
                    )
                )).scalar() or 0
                if flag_count > 0:
                    reasons.append(f"{flag_count} open high/critical fraud flag(s)")

                # ── 5. Tier amount limit ──────────────────────────────────
                currency = (req.currency or "NGN").upper()
                amount = req.amount or Decimal("0")
                if currency == "USD":
                    limit = TIER_LIMITS_USD.get(effective_tier, Decimal("100"))
                else:
                    limit = TIER_LIMITS_NGN.get(effective_tier, Decimal("150000"))

                if amount > limit:
                    reasons.append(
                        f"Amount {currency} {amount:.2f} exceeds {effective_tier} tier limit {limit:.2f}"
                    )

                # ── 6. 24-hour frequency check ────────────────────────────
                recent_count = (await db.execute(
                    select(func.count(WithdrawalRequest.id)).where(
                        WithdrawalRequest.user_id == req.user_id,
                        WithdrawalRequest.status.in_(["processed", "pending"]),
                        WithdrawalRequest.requested_at >= window_24h,
                        WithdrawalRequest.id != req.id,
                    )
                )).scalar() or 0
                if recent_count >= 2:
                    reasons.append(f"{recent_count} other withdrawals in last 24h")

                # ── Decision ──────────────────────────────────────────────
                if not reasons:
                    req.status = "processed"
                    req.reviewed_by = -1  # system
                    req.review_note = "Auto-approved by withdrawal gatekeeper agent"
                    req.processed_at = now
                    approved += 1
                    logger.info(
                        "[withdrawal-gatekeeper] AUTO-APPROVED req=%s user=%d %s %.2f",
                        req.id, req.user_id, currency, float(amount),
                    )
                else:
                    req.status = "manual_review"
                    req.review_note = "Auto-flagged: " + "; ".join(reasons)
                    manual += 1
                    logger.info(
                        "[withdrawal-gatekeeper] MANUAL_REVIEW req=%s user=%d reasons=%s",
                        req.id, req.user_id, reasons,
                    )

            await db.commit()

        # Telegram summary if any activity
        if approved + manual > 0:
            try:
                tg = TelegramAlert()
                await tg.send_message(
                    f"<b>💸 Withdrawal Gatekeeper</b>\n"
                    f"✅ Auto-approved: {approved}\n"
                    f"⚠️ Sent to manual review: {manual}",
                    AlertPriority.LOW,
                )
            except Exception:
                pass

        result = {"processed": approved + manual, "approved": approved, "manual_review": manual}
        logger.info("[withdrawal-gatekeeper] cycle: %s", result)
        return result
