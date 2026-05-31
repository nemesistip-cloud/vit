"""Network Guardian Agent — manages VIT DID registry and node credentials.

Every cycle:
1. Ensures every registered agent has a DID identity.
2. Issues/renews NodeContributionCredentials to top-contributing nodes.
3. Creates a NetworkSnapshot for time-series tracking.
4. Records its own network contribution.

Interval: 1 hour
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import func, select

from app.agents.base import BaseAgent
from app.db.database import AsyncSessionLocal
from app.modules.did.engine import (
    get_active_credentials,
    get_or_create_agent_identity,
    issue_credential,
)
from app.modules.network.models import NodeActivity, NetworkSnapshot

logger = logging.getLogger(__name__)

_NODE_ID = "did:vit:agent:network-guardian"

_ALL_AGENT_NAMES = [
    "oracle-node", "network-guardian",
    "performance-monitor", "weight-optimizer", "retrain-trigger",
    "match-scout", "news-sentinel", "odds-anomaly",
    "kyc-screener", "fraud-review", "withdrawal-gatekeeper",
    "marketplace-audit", "model-promoter", "analytics-reporter",
    "fixture-gap", "accumulator-publisher", "revenue-optimizer",
    "governance-executor", "self-healing", "audit-sentinel",
    "prediction-moderator", "live-match-tracker",
]


class NetworkGuardianAgent(BaseAgent):
    """Maintains the DID registry and issues node credentials."""

    def __init__(self) -> None:
        super().__init__(
            name="network-guardian",
            interval_seconds=3600,   # 1 hour
            initial_delay_seconds=90,
        )
        self.dids_created = 0
        self.vcs_issued = 0

    async def run_cycle(self) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            return await self._process(db)

    async def _process(self, db) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        since_24h = now - timedelta(hours=24)

        dids_created = 0
        vcs_issued = 0

        # 1. Ensure every agent has a DID
        for agent_name in _ALL_AGENT_NAMES:
            try:
                identity = await get_or_create_agent_identity(agent_name, db)
                created = identity.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created >= now - timedelta(seconds=10):
                    dids_created += 1
            except Exception as exc:
                logger.warning("[network-guardian] DID creation failed for %s: %s", agent_name, exc)

        # 2. Get top-contributing nodes in last 24h
        top_res = await db.execute(
            select(
                NodeActivity.node_id,
                NodeActivity.node_name,
                func.count(NodeActivity.id).label("count"),
                func.sum(NodeActivity.contribution_score).label("score"),
            )
            .where(NodeActivity.recorded_at >= since_24h)
            .group_by(NodeActivity.node_id, NodeActivity.node_name)
            .order_by(func.sum(NodeActivity.contribution_score).desc())
            .limit(10)
        )
        top_nodes = top_res.all()

        # 3. Issue NodeContributionCredentials to qualifying agents
        for node_id, node_name, count, score in top_nodes:
            if not node_id.startswith("did:vit:agent:"):
                continue
            agent_name = node_id.replace("did:vit:agent:", "")
            try:
                identity = await get_or_create_agent_identity(agent_name, db)
                existing = await get_active_credentials(identity.id, db)
                existing_types = {vc.credential_type for vc in existing}

                if "NodeContributionCredential" not in existing_types:
                    await issue_credential(
                        identity.id,
                        "NodeContributionCredential",
                        {
                            "agentName": agent_name,
                            "contributions24h": int(count),
                            "contributionScore": round(float(score or 0), 2),
                            "tier": _contribution_tier(float(score or 0)),
                            "issuedAt": now.isoformat(),
                        },
                        db,
                        valid_days=7,
                    )
                    vcs_issued += 1
            except Exception as exc:
                logger.warning("[network-guardian] VC issue failed for %s: %s", node_id, exc)

        # 4. Also ensure network-guardian itself has an OracleNodeCredential
        try:
            guardian_identity = await get_or_create_agent_identity("network-guardian", db)
            existing = await get_active_credentials(guardian_identity.id, db)
            if not any(vc.credential_type == "NetworkGuardianCredential" for vc in existing):
                await issue_credential(
                    guardian_identity.id,
                    "NetworkGuardianCredential",
                    {
                        "role": "NetworkGuardian",
                        "capabilities": ["did_issuance", "vc_issuance", "node_registry"],
                        "issuedAt": now.isoformat(),
                    },
                    db,
                    valid_days=30,
                )
                vcs_issued += 1
        except Exception as exc:
            logger.warning("[network-guardian] self-VC failed: %s", exc)

        # 5. Create NetworkSnapshot
        total_n = (await db.execute(
            select(func.count(func.distinct(NodeActivity.node_id)))
        )).scalar() or 0
        active_n = (await db.execute(
            select(func.count(func.distinct(NodeActivity.node_id))).where(
                NodeActivity.recorded_at >= now - timedelta(hours=1)
            )
        )).scalar() or 0
        total_c = (await db.execute(select(func.count(NodeActivity.id)))).scalar() or 0
        oracle_c = (await db.execute(
            select(func.count(NodeActivity.id)).where(
                NodeActivity.activity_type == "oracle_submit",
                NodeActivity.recorded_at >= since_24h,
            )
        )).scalar() or 0

        health = min(100.0, (active_n / max(total_n, 1)) * 100 + total_c / 20)
        snap = NetworkSnapshot(
            total_nodes=total_n,
            active_nodes=active_n,
            total_contributions=total_c,
            oracle_submissions=oracle_c,
            network_health_score=round(health, 1),
            top_nodes=[
                {"node_id": r[0], "name": r[1], "score": round(float(r[3] or 0), 2)}
                for r in top_nodes[:5]
            ],
        )
        db.add(snap)

        # 6. Record own contribution
        self.dids_created += dids_created
        self.vcs_issued += vcs_issued
        activity = NodeActivity(
            node_id=_NODE_ID,
            node_name="network-guardian",
            node_type="agent",
            activity_type="cycle",
            contribution_score=2.0 + vcs_issued * 0.5,
            activity_meta={
                "dids_created": dids_created,
                "vcs_issued": vcs_issued,
                "network_health": round(health, 1),
                "cycle": self.run_count,
            },
        )
        db.add(activity)
        await db.commit()

        result = {
            "dids_created": dids_created,
            "vcs_issued": vcs_issued,
            "network_snapshot": {
                "total_nodes": total_n,
                "active_nodes": active_n,
                "health_score": round(health, 1),
            },
            "lifetime_dids": self.dids_created,
            "lifetime_vcs": self.vcs_issued,
        }
        logger.info("[network-guardian] cycle complete: %s", result)
        return result


def _contribution_tier(score: float) -> str:
    if score >= 50:
        return "platinum"
    if score >= 20:
        return "gold"
    if score >= 10:
        return "silver"
    return "bronze"
