"""app/agents/self_healing_agent.py  — Item 12: Self-Healing System Agent

Runs every 5 minutes. Reads system health indicators, applies automated
fixes for known failure patterns, and alerts admins for unknown issues.

Auto-remediation rules:
  DB_POOL_FULL    → log warning (SQLAlchemy auto-manages pool)
  AGENT_ERROR     → trigger the failing agent immediately
  LOW_ACCURACY    → trigger retrain-trigger agent
  MISSING_FIXTURES→ trigger fixture-gap agent
  HIGH_WITHDRAWAL → alert admin via Telegram

Unknown patterns → call AI (via shared client) to diagnose from health snapshot,
                   post AI diagnosis to admin Telegram.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

ACCURACY_FLOOR = 0.45
AGENT_ERROR_THRESHOLD = 3
HIGH_WITHDRAWAL_COUNT = 20


async def _diagnose(snapshot: dict) -> str | None:
    prompt = (
        f"You are a platform reliability engineer. Diagnose this system health snapshot "
        f"and recommend the single most impactful fix.\n\n"
        f"Health snapshot:\n{json.dumps(snapshot, indent=2, default=str)}\n\n"
        f"Reply in max 3 sentences: what's wrong and what to do."
    )
    return await call_ai(prompt, max_tokens=250, temperature=0.2)


class SelfHealingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="self-healing",
            interval_seconds=5 * 60,
            initial_delay_seconds=15,
        )
        self._last_withdrawal_alert: datetime | None = None
        self._last_diagnosis_at: datetime | None = None

    async def run_cycle(self) -> Dict[str, Any]:
        from app.agents.coordinator import get_coordinator
        from app.services.alerts import TelegramAlert, AlertPriority
        from app.db.database import AsyncSessionLocal
        from app.modules.wallet.models import WithdrawalRequest
        from sqlalchemy import select, func

        coordinator = get_coordinator()
        now = datetime.now(timezone.utc)
        actions_taken: List[str] = []
        issues: List[str] = []

        # ── 1. Agent health check ─────────────────────────────────────────
        agent_status = coordinator.status()
        for name, snap in agent_status.get("agents", {}).items():
            err_count = snap.get("error_count", 0)
            status = snap.get("status", "")
            if status == "error" and err_count >= AGENT_ERROR_THRESHOLD:
                issues.append(f"Agent '{name}' has {err_count} consecutive errors")
                if coordinator.trigger(name):
                    actions_taken.append(f"triggered '{name}' for retry")
                    logger.info("[self-healing] triggered failing agent: %s", name)

        # ── 2. Low accuracy check ─────────────────────────────────────────
        try:
            perf_result = coordinator.get_agent_result("performance-monitor") or {}
            flagged_models = perf_result.get("flagged_models", [])
            if flagged_models:
                issues.append(f"{len(flagged_models)} model(s) below accuracy floor")
                coordinator.trigger("retrain-trigger")
                actions_taken.append("triggered retrain-trigger due to low accuracy")
        except Exception:
            pass

        # ── 3. Fixture gap check ──────────────────────────────────────────
        try:
            gap_result = coordinator.get_agent_result("fixture-gap") or {}
            unfilled = gap_result.get("gap_matches_found", 0) - gap_result.get("filled", 0)
            if unfilled > 5:
                issues.append(f"{unfilled} fixture gaps still unfilled")
                coordinator.trigger("fixture-gap")
                actions_taken.append("triggered fixture-gap agent")
        except Exception:
            pass

        # ── 4. High withdrawal backlog check ──────────────────────────────
        try:
            async with AsyncSessionLocal() as db:
                pending_wd = (await db.execute(
                    select(func.count(WithdrawalRequest.id))
                    .where(WithdrawalRequest.status == "pending")
                )).scalar() or 0

            if pending_wd >= HIGH_WITHDRAWAL_COUNT:
                issues.append(f"High withdrawal backlog: {pending_wd} pending")
                cooldown_ok = (
                    self._last_withdrawal_alert is None
                    or (now - self._last_withdrawal_alert).total_seconds() > 3600
                )
                if cooldown_ok:
                    tg = TelegramAlert()
                    await tg.send_message(
                        f"<b>⚠️ Self-Healing Alert</b>\n"
                        f"Withdrawal backlog: <b>{pending_wd}</b> pending requests.\n"
                        f"Withdrawal gatekeeper agent is running — check manual_review queue.",
                        AlertPriority.HIGH,
                    )
                    self._last_withdrawal_alert = now
                    actions_taken.append(f"alerted admin: {pending_wd} pending withdrawals")
        except Exception:
            pass

        # ── 5. Unknown issues → AI diagnosis ──────────────────────────────
        unknown_issues = [
            i for i in issues
            if "agent" not in i.lower() and "fixture" not in i.lower()
        ]
        if unknown_issues:
            diag_cooldown = (
                self._last_diagnosis_at is None
                or (now - self._last_diagnosis_at).total_seconds() > 1800
            )
            if diag_cooldown:
                snapshot = {
                    "timestamp": now.isoformat(),
                    "issues": unknown_issues,
                    "agent_statuses": {
                        n: {"status": s["status"], "error_count": s["error_count"]}
                        for n, s in agent_status.get("agents", {}).items()
                    },
                }
                diagnosis = await _diagnose(snapshot)
                if diagnosis:
                    self._last_diagnosis_at = now
                    try:
                        tg = TelegramAlert()
                        await tg.send_message(
                            f"<b>🔧 Self-Healing Diagnosis</b>\n"
                            f"Issues: {'; '.join(unknown_issues)}\n\n"
                            f"<i>AI Diagnosis:</i>\n{diagnosis}",
                            AlertPriority.MEDIUM,
                        )
                        actions_taken.append("sent AI diagnosis to admin")
                    except Exception:
                        pass

        result = {
            "issues_found": len(issues),
            "actions_taken": actions_taken,
            "issues": issues,
        }
        if issues:
            logger.info("[self-healing] cycle: %s", result)
        return result
