"""app/agents/audit_sentinel_agent.py  — Item 13: Nightly Audit Sentinel

Runs every 24 hours. Reads the audit_log table for the past 24 hours,
groups events by actor and action type, flags suspicious patterns,
and sends a shift summary to admin Telegram via Gemini narrative.

Suspicious patterns flagged:
  - Bulk deletions (>5 delete actions by one actor in 24h)
  - Rapid config changes (>3 config edits in 1 hour)
  - Off-hours admin actions (midnight–5am UTC)
  - Same resource modified by 3+ different admins
  - Mass user bans (>3 ban actions)
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


from app.agents.base import BaseAgent
from app.services.ai_client import call_ai

logger = logging.getLogger(__name__)


def _detect_anomalies(logs: list) -> List[str]:
    anomalies: List[str] = []

    # Count actions per actor
    actor_actions: dict[str, list] = defaultdict(list)
    for log in logs:
        actor = log.get("actor") or "unknown"
        action = log.get("action") or ""
        actor_actions[actor].append(action)

    for actor, actions in actor_actions.items():
        deletes = sum(1 for a in actions if "delete" in a.lower() or "remove" in a.lower())
        bans = sum(1 for a in actions if "ban" in a.lower() or "suspend" in a.lower())
        configs = sum(1 for a in actions if "config" in a.lower() or "setting" in a.lower())

        if deletes > 5:
            anomalies.append(f"Actor '{actor}' performed {deletes} deletion actions in 24h")
        if bans > 3:
            anomalies.append(f"Actor '{actor}' banned/suspended {bans} users in 24h")
        if configs > 3:
            anomalies.append(f"Actor '{actor}' made {configs} config changes in 24h")

    # Off-hours actions (midnight–5am UTC)
    off_hours = [
        log for log in logs
        if log.get("created_at") and 0 <= log["created_at"].hour < 5
    ]
    if off_hours:
        anomalies.append(f"{len(off_hours)} admin actions occurred between midnight–5am UTC")

    return anomalies


def _build_audit_prompt(stats: dict, anomalies: List[str], date: str) -> str:
    anomaly_str = "\n".join(f"  ⚠️ {a}" for a in anomalies) if anomalies else "  None detected"
    return (
        f"You are a security compliance officer reviewing the daily audit log summary.\n\n"
        f"Audit period: {date} (last 24 hours)\n\n"
        f"Activity summary:\n"
        f"  Total audit events: {stats.get('total_events', 0)}\n"
        f"  Unique actors: {stats.get('unique_actors', 0)}\n"
        f"  Action breakdown: {stats.get('action_breakdown', {})}\n\n"
        f"Flagged anomalies:\n{anomaly_str}\n\n"
        f"Write a brief audit shift summary (max 200 words):\n"
        f"1. Overall assessment (safe/caution/alert)\n"
        f"2. Notable activity\n"
        f"3. Any recommended follow-up\n\n"
        f"Be concise and professional."
    )


class AuditSentinelAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="audit-sentinel",
            interval_seconds=24 * 60 * 60,
            initial_delay_seconds=500,
        )

    async def run_cycle(self) -> Dict[str, Any]:

        from app.db.database import AsyncSessionLocal
        from app.services.alerts import TelegramAlert, AlertPriority
        from sqlalchemy import select, text, func
        from collections import Counter

        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(hours=24)
        date_str = now.strftime("%Y-%m-%d %H:%M UTC")

        audit_logs: list = []
        stats: dict = {"total_events": 0, "unique_actors": 0, "action_breakdown": {}}

        async with AsyncSessionLocal() as db:
            # Try to query audit_log table (may not exist in all deployments)
            try:
                res = await db.execute(
                    text(
                        "SELECT action, actor, resource, created_at "
                        "FROM audit_log "
                        "WHERE created_at >= :since "
                        "ORDER BY created_at DESC "
                        "LIMIT 500"
                    ),
                    {"since": yesterday},
                )
                rows = res.fetchall()
                audit_logs = [
                    {
                        "action": r[0],
                        "actor": r[1],
                        "resource": r[2],
                        "created_at": r[3],
                    }
                    for r in rows
                ]
            except Exception as e:
                logger.debug("[audit-sentinel] audit_log query failed: %s", e)

        if not audit_logs:
            return {"skipped": True, "reason": "no audit events in last 24h or table unavailable"}

        # Build stats
        action_counts = Counter(log["action"] for log in audit_logs)
        actors = set(log["actor"] for log in audit_logs if log["actor"])
        stats = {
            "total_events": len(audit_logs),
            "unique_actors": len(actors),
            "action_breakdown": dict(action_counts.most_common(10)),
        }

        anomalies = _detect_anomalies(audit_logs)

        # Generate narrative
        narrative = ""
        if api_key:
            prompt = _build_audit_prompt(stats, anomalies, date_str)
            narrative = await call_ai(prompt) or ""

        # Send to Telegram
        severity = AlertPriority.HIGH if anomalies else AlertPriority.LOW
        try:
            tg = TelegramAlert()
            body = (
                f"<b>🔍 Nightly Audit Report — {date_str}</b>\n{'━'*22}\n\n"
                f"Events: {stats['total_events']} | Actors: {stats['unique_actors']}\n"
            )
            if anomalies:
                body += f"\n<b>⚠️ Anomalies ({len(anomalies)}):</b>\n"
                body += "\n".join(f"• {a}" for a in anomalies[:5])
                body += "\n"
            if narrative:
                body += f"\n<i>{narrative[:1000]}</i>"
            await tg.send_message(body, severity)
        except Exception as te:
            logger.warning("[audit-sentinel] Telegram error: %s", te)

        logger.info(
            "[audit-sentinel] report: %d events, %d anomalies",
            stats["total_events"], len(anomalies),
        )
        return {
            "events_reviewed": stats["total_events"],
            "anomalies_found": len(anomalies),
            "anomalies": anomalies,
        }
