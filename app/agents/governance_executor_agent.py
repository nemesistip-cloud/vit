"""app/agents/governance_executor_agent.py  — Item 11: Governance Auto-Executor

Runs every 10 minutes. Polls governance proposals with status='passed'
where the timelock period has elapsed, and automatically executes them.

Timelock check: now - passed_at >= proposal.timelock_seconds

After execution: sends Telegram alert with proposal details.
Failed executions are logged and retried on the next cycle.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

MAX_PER_CYCLE = 10


class GovernanceExecutorAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="governance-executor",
            interval_seconds=10 * 60,
            initial_delay_seconds=60,
        )
        self._failed_ids: set[int] = set()  # track permanently failed proposals

    async def run_cycle(self) -> Dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.modules.governance.models import Proposal
        from app.modules.governance.service import execute_proposal
        from app.services.alerts import TelegramAlert, AlertPriority
        from sqlalchemy import select

        executed = skipped = failed = closed = 0
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            # ── Auto-close expired active proposals ─────────────────────
            try:
                expired_res = await db.execute(
                    select(Proposal)
                    .where(
                        Proposal.status == "active",
                        Proposal.voting_ends_at.isnot(None),
                        Proposal.voting_ends_at < now,
                    )
                    .limit(MAX_PER_CYCLE)
                )
                expired = expired_res.scalars().all()
                for ep in expired:
                    # Determine outcome: passed if votes_for > votes_against and quorum met
                    quorum = getattr(ep, "quorum_required", 1000.0) or 1000.0
                    total_votes = (ep.votes_for or 0) + (ep.votes_against or 0)
                    if (ep.votes_for or 0) > (ep.votes_against or 0) and total_votes >= quorum:
                        ep.status = "passed"
                        logger.info(
                            "[governance-executor] proposal=%d PASSED at deadline "
                            "(for=%.0f against=%.0f quorum=%.0f)",
                            ep.id, ep.votes_for or 0, ep.votes_against or 0, quorum,
                        )
                    else:
                        ep.status = "failed"
                        logger.info(
                            "[governance-executor] proposal=%d FAILED at deadline "
                            "(for=%.0f against=%.0f quorum=%.0f total=%.0f)",
                            ep.id, ep.votes_for or 0, ep.votes_against or 0, quorum, total_votes,
                        )
                    closed += 1
                if closed:
                    await db.commit()
            except Exception as _close_err:
                logger.error("[governance-executor] auto-close error: %s", _close_err)

            res = await db.execute(
                select(Proposal)
                .where(Proposal.status == "passed")
                .order_by(Proposal.updated_at.asc())
                .limit(MAX_PER_CYCLE)
            )
            proposals = res.scalars().all()

            for proposal in proposals:
                if proposal.id in self._failed_ids:
                    skipped += 1
                    continue

                # Check timelock
                passed_at = proposal.updated_at or proposal.created_at
                if passed_at and passed_at.tzinfo is None:
                    passed_at = passed_at.replace(tzinfo=timezone.utc)

                timelock = getattr(proposal, "timelock_seconds", 86400)
                if passed_at:
                    elapsed = (now - passed_at).total_seconds()
                    if elapsed < timelock:
                        remaining_h = int((timelock - elapsed) / 3600)
                        logger.debug(
                            "[governance-executor] proposal=%d timelock %dh remaining",
                            proposal.id, remaining_h,
                        )
                        skipped += 1
                        continue

                # Execute
                try:
                    await execute_proposal(db, proposal.id)
                    executed += 1
                    logger.info(
                        "[governance-executor] EXECUTED proposal=%d title=%s",
                        proposal.id, proposal.title,
                    )

                    try:
                        tg = TelegramAlert()
                        await tg.send_message(
                            f"<b>⚖️ Governance Proposal Executed</b>\n"
                            f"ID: {proposal.id} — {proposal.title}\n"
                            f"Passed votes: {proposal.votes_for:.0f} for, "
                            f"{proposal.votes_against:.0f} against\n"
                            f"<i>Auto-executed after {timelock // 3600}h timelock</i>",
                            AlertPriority.MEDIUM,
                        )
                    except Exception:
                        pass

                except Exception as e:
                    failed += 1
                    self._failed_ids.add(proposal.id)
                    logger.error(
                        "[governance-executor] FAILED proposal=%d: %s",
                        proposal.id, e,
                    )

        result = {"proposals_checked": len(proposals), "executed": executed, "skipped": skipped, "failed": failed, "auto_closed": closed}
        if executed > 0 or closed > 0:
            logger.info("[governance-executor] cycle: %s", result)
        return result
