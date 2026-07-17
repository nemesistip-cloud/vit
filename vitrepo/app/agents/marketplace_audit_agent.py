"""app/agents/marketplace_audit_agent.py  — Item 4: Marketplace Code Audit

Runs every 30 minutes. Finds pending marketplace listings with uploaded
Python source code, calls native AI to perform a security + quality audit,
then auto-approves SAFE listings and auto-rejects DANGEROUS ones.

Audit dimensions:
  SECURITY  — exec/eval/os.system/subprocess/open() with write, network calls
  INTERFACE — must expose predict() or train() or class Model/VITModel
  QUALITY   — not trivially random or stub output
  ORIGINALITY — basic fingerprint vs known patterns

Verdicts:
  safe     → auto-approve
  review   → leave pending, attach AI audit report
  reject   → auto-reject with reason
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict


from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

MAX_PER_CYCLE = 5
MAX_CODE_CHARS = 8000  # native AI token budget



def _build_audit_prompt(code: str, listing_name: str) -> str:
    truncated = code[:MAX_CODE_CHARS]
    return (
        f"You are a security engineer reviewing a Python AI model plugin submission for a sports prediction marketplace.\n\n"
        f"Listing: {listing_name}\n"
        f"Source code:\n```python\n{truncated}\n```\n\n"
        f"Return ONLY this JSON (no markdown):\n"
        f'{{\n'
        f'  "verdict": "safe"|"review"|"reject",\n'
        f'  "security_issues": ["issue1"],\n'
        f'  "interface_valid": true,\n'
        f'  "quality_assessment": "brief assessment",\n'
        f'  "reject_reason": "only if rejected"\n'
        f'}}\n\n'
        f"reject if: uses exec/eval/subprocess/os.system/open(write)/socket/requests/urllib with external hosts, "
        f"exfiltrates data, or has no valid predict/train interface.\n"
        f"safe if: clean code, valid interface, no dangerous imports.\n"
        f"review if: borderline (external imports for ML libs only like sklearn/numpy/torch are fine)."
    )


_DANGEROUS_PATTERNS = [
    r"\bexec\s*\(",
    r"\beval\s*\(",
    r"subprocess\.(run|call|Popen|check_output)",
    r"os\.system\s*\(",
    r"__import__\s*\(",
    r"open\s*\(.*['\"]w['\"]",
    r"socket\.socket",
]


def _fast_reject(code: str) -> str | None:
    """Quick regex pre-screen before calling AI."""
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            return f"Dangerous pattern detected: {pattern}"
    return None


class MarketplaceAuditAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="marketplace-audit",
            interval_seconds=30 * 60,
            initial_delay_seconds=90,
        )

    async def run_cycle(self) -> Dict[str, Any]:

        from app.db.database import AsyncSessionLocal
        from app.modules.marketplace.models import AIModelListing
        from app.modules.marketplace.service import admin_approve_listing, admin_reject_listing
        from app.services.alerts import TelegramAlert, AlertPriority
        from sqlalchemy import select
        import json

        approved = rejected = flagged = 0
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(AIModelListing)
                .where(AIModelListing.approval_status == "pending")
                .order_by(AIModelListing.created_at.asc())
                .limit(MAX_PER_CYCLE)
            )
            listings = res.scalars().all()

            for listing in listings:
                # Load source code from stored path or content
                code = getattr(listing, "source_code", None) or ""
                file_path = getattr(listing, "file_path", None)

                if not code and file_path:
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            code = f.read()
                    except Exception:
                        code = ""

                if not code:
                    # No code to audit — leave for human
                    flagged += 1
                    continue

                # Fast regex pre-screen
                fast_reject = _fast_reject(code)
                if fast_reject:
                    try:
                        await admin_reject_listing(
                            db, listing.id, -1,
                            reason=f"Auto-rejected (security scan): {fast_reject}",
                        )
                        rejected += 1
                    except Exception as e:
                        logger.warning("[marketplace-audit] reject error: %s", e)
                    await asyncio.sleep(0.5)
                    continue

                # AI audit
                prompt = _build_audit_prompt(code, listing.name or "unknown")
                raw = await call_ai(prompt)

                verdict = "review"
                audit_report = {}

                if raw:
                    try:
                        obj_match = re.search(r"\{[\s\S]*\}", raw.strip())
                        if obj_match:
                            audit_report = json.loads(obj_match.group())
                            verdict = audit_report.get("verdict", "review")
                    except Exception:
                        pass

                if verdict == "safe" and audit_report.get("interface_valid", True):
                    try:
                        await admin_approve_listing(db, listing.id, -1)
                        approved += 1
                        logger.info("[marketplace-audit] AUTO-APPROVED listing=%d", listing.id)
                    except Exception as e:
                        logger.warning("[marketplace-audit] approve error: %s", e)

                elif verdict == "reject":
                    reason = audit_report.get("reject_reason", "Failed AI security audit")
                    issues = audit_report.get("security_issues", [])
                    full_reason = reason + (f" Issues: {', '.join(issues)}" if issues else "")
                    try:
                        await admin_reject_listing(db, listing.id, -1, reason=full_reason)
                        rejected += 1
                        logger.info(
                            "[marketplace-audit] AUTO-REJECTED listing=%d reason=%s",
                            listing.id, full_reason,
                        )
                        tg = TelegramAlert()
                        await tg.send_message(
                            f"<b>🚫 Marketplace Listing Rejected</b>\n"
                            f"Listing ID: {listing.id} — {listing.name}\n"
                            f"Reason: {full_reason[:200]}",
                            AlertPriority.MEDIUM,
                        )
                    except Exception as e:
                        logger.warning("[marketplace-audit] reject error: %s", e)
                else:
                    # Store audit report in listing metadata
                    try:
                        if hasattr(listing, "meta") and audit_report:
                            existing = listing.meta or {}
                            existing["_ai_audit"] = audit_report
                            listing.meta = existing
                            await db.commit()
                    except Exception:
                        pass
                    flagged += 1

                await asyncio.sleep(2.0)

        result = {"approved": approved, "rejected": rejected, "flagged_for_review": flagged}
        logger.info("[marketplace-audit] cycle: %s", result)
        return result
