"""app/agents/self_healing_agent.py — Self-Healing System Agent v2

Runs every 5 minutes. Reads system health indicators, applies automated
fixes for known failure patterns, and alerts admins for unknown issues.

v2 upgrades:
  - Cascade restart prevention: per-agent cooldown (10 min) before re-triggering
  - VIT-Chain block-age check: alert if no block mined in last 30 min
  - Swarm efficiency gate: alert if overall efficiency drops below 70%
  - Accuracy velocity check: flag if >2 models drop >5% accuracy in one cycle
  - Richer issue categorization and structured action log

Auto-remediation rules:
  AGENT_ERROR       → trigger failing agent (with 10-min per-agent cooldown)
  LOW_ACCURACY      → trigger retrain-trigger agent
  MISSING_FIXTURES  → trigger fixture-gap agent
  HIGH_WITHDRAWAL   → alert admin via Telegram (1 h cooldown)
  CHAIN_STALLED     → alert admin + emit swarm event
  LOW_EFFICIENCY    → alert admin (2 h cooldown)
  ACCURACY_VELOCITY → alert admin + trigger retrain
  Unknown patterns  → call AI to diagnose, post diagnosis to admin Telegram
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)

ACCURACY_FLOOR           = 0.45
AGENT_ERROR_THRESHOLD    = 3
HIGH_WITHDRAWAL_COUNT    = 20
CHAIN_STALE_MINUTES      = 30       # alert if no block mined in this window
EFFICIENCY_FLOOR         = 0.70     # swarm avg efficiency below this → alert
ACCURACY_DROP_THRESHOLD  = 0.05     # per-model accuracy drop in one cycle that counts
ACCURACY_DROP_MAX_MODELS = 2        # how many models can drop before alert fires
TRIGGER_COOLDOWN_MINUTES = 10       # per-agent trigger cooldown


async def _diagnose(snapshot: dict) -> Optional[Dict[str, Any]]:
    """Enhanced diagnosis using recent logs and DeepSeek."""
    from app.core.log_buffer import log_buffer
    logs = log_buffer.get_logs()

    logs_text = "\n".join(logs)
    snapshot_text = json.dumps(snapshot, indent=2, default=str)
    from app.config import APP_NAME
    prompt = f"""
    You are a Platform Reliability Engineer for {APP_NAME}.
    Analyze this system health snapshot and recent logs to diagnose the root cause of the issues.

    Health Snapshot:
    {snapshot_text}

    Recent Logs (Last 100 lines):
    {logs_text}

    Identify the core issue and recommend a specific recovery action.
    Return a JSON object with:
    "diagnosis": "What is wrong and why",
    "recommendation": "What should be done",
    "recovery_action": "RESTART_MODEL_ORCHESTRATOR" | "CLEAR_CACHE" | "TRIGGER_AGENT" | "NONE",
    "target_agent": "agent_name_if_applicable"
    """

    try:
        from app.services.ai_client import call_ai
        response = await call_ai(
            prompt=prompt,
            temperature=0.2
        )
        # Attempt to parse JSON
        clean_json = response.strip().replace("```json", "").replace("```", "")
        import json as _json
        return _json.loads(clean_json)
    except Exception as e:
        logger.error(f"Self-healing AI diagnosis failed: {e}")
        return None


class SelfHealingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="self-healing",
            interval_seconds=5 * 60,
            initial_delay_seconds=15,
        )
        # Cooldown tracking
        self._last_withdrawal_alert: Optional[datetime]  = None
        self._last_diagnosis_at:     Optional[datetime]  = None
        self._last_efficiency_alert: Optional[datetime]  = None
        self._last_chain_alert:      Optional[datetime]  = None
        # Per-agent trigger timestamps (cascade prevention)
        self._triggered_at: Dict[str, datetime]          = {}

    def _can_trigger(self, agent_name: str) -> bool:
        """Return True if this agent hasn't been triggered within the cooldown window."""
        last = self._triggered_at.get(agent_name)
        if last is None:
            return True
        return (datetime.now(timezone.utc) - last).total_seconds() > TRIGGER_COOLDOWN_MINUTES * 60

    def _record_trigger(self, agent_name: str) -> None:
        self._triggered_at[agent_name] = datetime.now(timezone.utc)

    async def run_cycle(self) -> Dict[str, Any]:
        from app.core.swarm_orchestrator import get_swarm
        from app.services.alerts import TelegramAlert, AlertPriority
        from app.db.database import AsyncSessionLocal
        from app.modules.wallet.models import WithdrawalRequest
        from sqlalchemy import select, func

        swarm  = get_swarm()
        now    = datetime.now(timezone.utc)
        actions_taken: List[str] = []
        issues:        List[str] = []

        # ── 1. Agent health check (with cascade-restart prevention) ───────────
        agent_status = swarm.status()
        for name, snap in agent_status.get("agents", {}).items():
            err_count = snap.get("error_count", 0)
            status    = snap.get("status", "")
            if status == "error" and err_count >= AGENT_ERROR_THRESHOLD:
                issues.append(f"Agent '{name}' has {err_count} consecutive errors")
                if self._can_trigger(name):
                    if swarm.trigger(name):
                        self._record_trigger(name)
                        actions_taken.append(f"triggered '{name}' for retry")
                        logger.info("[self-healing] triggered failing agent: %s", name)
                        await swarm.emit_event("agent_healed", self.name,
                                               {"target": name, "err_count": err_count})
                else:
                    actions_taken.append(f"'{name}' still in trigger cooldown — skipped")

        # ── 2. Low accuracy check ──────────────────────────────────────────────
        try:
            perf_result   = swarm.get_agent_result("performance-monitor") or {}
            flagged_models = perf_result.get("flagged_models", [])
            if flagged_models:
                issues.append(f"{len(flagged_models)} model(s) below accuracy floor")
                if self._can_trigger("retrain-trigger"):
                    swarm.trigger("retrain-trigger")
                    self._record_trigger("retrain-trigger")
                    actions_taken.append("triggered retrain-trigger due to low accuracy")
        except Exception:
            pass

        # ── 3. Accuracy velocity check (rapid accuracy drops) ─────────────────
        try:
            perf_result  = swarm.get_agent_result("performance-monitor") or {}
            velocities   = perf_result.get("accuracy_velocity", {})
            rapid_drops  = [
                k for k, delta in velocities.items()
                if delta <= -ACCURACY_DROP_THRESHOLD
            ]
            if len(rapid_drops) >= ACCURACY_DROP_MAX_MODELS:
                issues.append(
                    f"Rapid accuracy drop: {len(rapid_drops)} models fell "
                    f"≥{ACCURACY_DROP_THRESHOLD*100:.0f}% in one cycle"
                )
                if self._can_trigger("retrain-trigger"):
                    swarm.trigger("retrain-trigger")
                    self._record_trigger("retrain-trigger")
                    actions_taken.append(
                        f"triggered retrain-trigger: accuracy velocity alert ({rapid_drops})"
                    )
                    await swarm.emit_event("accuracy_velocity_alert", self.name,
                                           {"models": rapid_drops})
        except Exception:
            pass

        # ── 4. Fixture gap check ───────────────────────────────────────────────
        try:
            gap_result = swarm.get_agent_result("fixture-gap") or {}
            unfilled   = gap_result.get("gap_matches_found", 0) - gap_result.get("filled", 0)
            if unfilled > 5:
                issues.append(f"{unfilled} fixture gaps still unfilled")
                if self._can_trigger("fixture-gap"):
                    swarm.trigger("fixture-gap")
                    self._record_trigger("fixture-gap")
                    actions_taken.append("triggered fixture-gap agent")
        except Exception:
            pass

        # ── 5. VIT-Chain block-age check ───────────────────────────────────────
        try:
            from vit_chain import get_vit_chain
            chain       = get_vit_chain()
            chain_stats = await chain.get_chain_stats()
            # Check latest block timestamp via recent blocks query
            recent = await chain.get_blocks(limit=1)
            blocks = recent.get("blocks", [])
            if blocks:
                last_ts_raw = blocks[0].get("timestamp", "")
                last_ts     = datetime.fromisoformat(last_ts_raw.replace("Z", "+00:00"))
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                block_age_min = (now - last_ts).total_seconds() / 60

                if block_age_min > CHAIN_STALE_MINUTES:
                    issues.append(
                        f"VIT-Chain stalled: last block {block_age_min:.0f} min ago "
                        f"(threshold {CHAIN_STALE_MINUTES} min)"
                    )
                    chain_alert_ok = (
                        self._last_chain_alert is None
                        or (now - self._last_chain_alert).total_seconds() > 3600
                    )
                    if chain_alert_ok:
                        self._last_chain_alert = now
                        await swarm.emit_event("chain_stalled", self.name, {
                            "last_block_minutes_ago": round(block_age_min, 1),
                            "block_count":            chain_stats.get("blocks"),
                        })
                        try:
                            tg = TelegramAlert()
                            await tg.send_message(
                                f"<b>⛓️ VIT-Chain Alert</b>\n"
                                f"No new block for <b>{block_age_min:.0f} minutes</b>.\n"
                                f"Chain may be stalled. Block count: {chain_stats.get('blocks')}.",
                                AlertPriority.HIGH,
                            )
                            actions_taken.append(
                                f"alerted admin: chain stalled {block_age_min:.0f} min"
                            )
                        except Exception:
                            pass
        except Exception:
            pass

        # ── 6. High withdrawal backlog check ──────────────────────────────────
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
                    self._last_withdrawal_alert = now
                    try:
                        tg = TelegramAlert()
                        await tg.send_message(
                            f"<b>⚠️ Self-Healing Alert</b>\n"
                            f"Withdrawal backlog: <b>{pending_wd}</b> pending requests.\n"
                            f"Withdrawal gatekeeper agent is running — check manual_review queue.",
                            AlertPriority.HIGH,
                        )
                        actions_taken.append(f"alerted admin: {pending_wd} pending withdrawals")
                    except Exception:
                        pass
        except Exception:
            pass

        # ── 7. Swarm efficiency gate ───────────────────────────────────────────
        try:
            health = swarm.health_summary()
            avg_eff = health.get("avg_efficiency", 1.0)
            if avg_eff < EFFICIENCY_FLOOR:
                issues.append(
                    f"Swarm efficiency low: {avg_eff:.1%} "
                    f"(floor {EFFICIENCY_FLOOR:.0%})"
                )
                eff_alert_ok = (
                    self._last_efficiency_alert is None
                    or (now - self._last_efficiency_alert).total_seconds() > 7200
                )
                if eff_alert_ok:
                    self._last_efficiency_alert = now
                    await swarm.emit_event("low_swarm_efficiency", self.name,
                                           {"avg_efficiency": avg_eff})
                    try:
                        tg = TelegramAlert()
                        await tg.send_message(
                            f"<b>🤖 Swarm Efficiency Alert</b>\n"
                            f"Average agent efficiency: <b>{avg_eff:.1%}</b> "
                            f"(below {EFFICIENCY_FLOOR:.0%} floor).\n"
                            f"Check agent logs for recurring errors.",
                            AlertPriority.MEDIUM,
                        )
                        actions_taken.append(f"alerted admin: swarm efficiency {avg_eff:.1%}")
                    except Exception:
                        pass
        except Exception:
            pass

        # ── 8. Unknown issues → AI diagnosis ──────────────────────────────────
        unknown_issues = [
            i for i in issues
            if not any(kw in i.lower() for kw in ("agent", "fixture", "withdrawal", "chain"))
        ]
        if unknown_issues:
            diag_cooldown = (
                self._last_diagnosis_at is None
                or (now - self._last_diagnosis_at).total_seconds() > 1800
            )
            if diag_cooldown:
                snapshot = {
                    "timestamp":    now.isoformat(),
                    "issues":       unknown_issues,
                    "agent_statuses": {
                        n: {"status": s.get("status"), "error_count": s.get("error_count")}
                        for n, s in agent_status.get("agents", {}).items()
                    },
                }
                diag_result = await _diagnose(snapshot)
                if diag_result:
                    diagnosis = diag_result.get("diagnosis", "Unknown diagnosis")
                    recommendation = diag_result.get("recommendation", "No specific recommendation")
                    recovery_action = diag_result.get("recovery_action", "NONE")

                    self._last_diagnosis_at = now

                    # Execute AI-recommended recovery if safe
                    if recovery_action == "TRIGGER_AGENT":
                        target = diag_result.get("target_agent")
                        if target and self._can_trigger(target):
                            swarm.trigger(target)
                            self._record_trigger(target)
                            actions_taken.append(f"AI-RECOVERY: Triggered agent '{target}'")
                    elif recovery_action == "CLEAR_CACHE":
                        from app.services.cache import get_cache
                        cache = get_cache()
                        await cache.clear_all()
                        actions_taken.append("AI-RECOVERY: Cleared system cache")

                    try:
                        tg = TelegramAlert()
                        await tg.send_message(
                            f"<b>🔧 DeepSeek Self-Healing Diagnosis</b>\n"
                            f"Issues: {'; '.join(unknown_issues)}\n\n"
                            f"<b>Diagnosis:</b> {diagnosis}\n"
                            f"<b>Rec:</b> {recommendation}\n"
                            f"<b>Action:</b> {recovery_action}",
                            AlertPriority.MEDIUM,
                        )
                        actions_taken.append("sent AI diagnosis to admin")
                    except Exception:
                        pass

        result = {
            "issues_found":  len(issues),
            "actions_taken": actions_taken,
            "issues":        issues,
        }
        if issues:
            logger.info("[self-healing] cycle: %s", result)
        return result
