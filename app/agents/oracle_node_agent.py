"""Oracle Node Agent — acts as an internal VIT oracle node.

Monitors matches with known results in DB and submits them to the oracle
consensus system as source "vit-node-internal". Tracks contribution to
the network via NodeActivity records.

Interval: 10 minutes
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import select

from app.agents.base import BaseAgent
from app.db.database import AsyncSessionLocal
from app.db.models import Match
from app.modules.blockchain.models import OracleResult, ConsensusPrediction, ConsensusStatus
from app.modules.blockchain.settlement import settle_match
from app.modules.network.models import NodeActivity

logger = logging.getLogger(__name__)

_NODE_ID = "did:vit:agent:oracle-node"
_SOURCE = "vit-node-internal"
_MIN_AGREEMENT = 2


class OracleNodeAgent(BaseAgent):
    """Submits confirmed match results to the oracle consensus engine."""

    def __init__(self) -> None:
        super().__init__(
            name="oracle-node",
            interval_seconds=600,   # 10 minutes
            initial_delay_seconds=45,
        )
        self.submitted_count = 0
        self.settled_count = 0

    async def run_cycle(self) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            return await self._process(db)

    async def _process(self, db) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=6)

        # Find finished matches with actual_outcome that don't already have
        # a vit-node-internal oracle submission
        finished_res = await db.execute(
            select(Match).where(
                Match.actual_outcome.isnot(None),
                Match.status == "finished",
                Match.kickoff_time >= lookback,
            ).limit(20)
        )
        finished_matches = finished_res.scalars().all()

        submitted = 0
        settled = 0
        skipped = 0

        for match in finished_matches:
            match_id = str(match.id)

            # Check already submitted by this node
            existing_res = await db.execute(
                select(OracleResult).where(
                    OracleResult.match_id == match_id,
                    OracleResult.source == _SOURCE,
                )
            )
            if existing_res.scalar_one_or_none():
                skipped += 1
                continue

            outcome = match.actual_outcome
            home_g = match.home_goals or 0
            away_g = match.away_goals or 0

            oracle_rec = OracleResult(
                match_id=match_id,
                source=_SOURCE,
                home_score=home_g,
                away_score=away_g,
                result=outcome,
                submitted_at=datetime.utcnow(),
            )
            db.add(oracle_rec)
            await db.flush()
            submitted += 1

            # Check consensus
            all_res = await db.execute(
                select(OracleResult).where(OracleResult.match_id == match_id)
            )
            all_oracle = all_res.scalars().all()

            outcome_counts: dict[str, int] = {}
            for r in all_oracle:
                outcome_counts[r.result] = outcome_counts.get(r.result, 0) + 1

            agreed: str | None = None
            for ov, cnt in outcome_counts.items():
                if cnt >= _MIN_AGREEMENT:
                    agreed = ov
                    break

            if agreed:
                for r in all_oracle:
                    r.is_accepted = r.result == agreed
                await db.flush()

                cp_res = await db.execute(
                    select(ConsensusPrediction).where(
                        ConsensusPrediction.match_id == match_id
                    )
                )
                cp = cp_res.scalar_one_or_none()
                if cp and cp.status not in (
                    ConsensusStatus.SETTLED.value,
                    ConsensusStatus.VOIDED.value,
                ):
                    try:
                        await settle_match(match_id, agreed, db)
                        settled += 1
                        logger.info(
                            "[oracle-node] settled match %s → %s", match_id, agreed
                        )
                    except Exception as exc:
                        logger.warning(
                            "[oracle-node] settlement failed for %s: %s", match_id, exc
                        )

        # Record network contribution
        if submitted > 0:
            self.submitted_count += submitted
            self.settled_count += settled
            activity = NodeActivity(
                node_id=_NODE_ID,
                node_name="oracle-node",
                node_type="agent",
                activity_type="oracle_submit",
                contribution_score=float(submitted) * 2.0,
                activity_meta={
                    "submitted": submitted,
                    "settled": settled,
                    "skipped": skipped,
                    "cycle": self.run_count,
                },
            )
            db.add(activity)

        await db.commit()

        result = {
            "submitted": submitted,
            "settled": settled,
            "skipped": skipped,
            "lifetime_submitted": self.submitted_count,
            "lifetime_settled": self.settled_count,
        }
        logger.info("[oracle-node] cycle complete: %s", result)
        return result
