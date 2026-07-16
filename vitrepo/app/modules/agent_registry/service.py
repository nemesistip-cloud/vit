"""AI Agent Registry Service — registration, staking, performance, payment routing."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent_registry.models import (
    AgentCredential,
    AgentPaymentRoute,
    AgentPerformanceRecord,
    AgentStatus,
    AIAgentRegistration,
    CredentialStatus,
)

logger = logging.getLogger(__name__)

BUILTIN_AGENTS = [
    {"agent_id": "vit-live-match-tracker", "name": "Live Match Tracker", "capabilities": ["data_processing", "oracle"]},
    {"agent_id": "vit-prediction-engine", "name": "VIT Prediction Engine", "capabilities": ["prediction"]},
    {"agent_id": "vit-oracle-aggregator", "name": "Oracle Data Aggregator", "capabilities": ["oracle", "verification"]},
    {"agent_id": "vit-network-guardian", "name": "Network Guardian", "capabilities": ["verification", "governance"]},
    {"agent_id": "vit-settlement-agent", "name": "Settlement Agent", "capabilities": ["prediction", "trading"]},
    {"agent_id": "vit-risk-monitor", "name": "Risk Monitor", "capabilities": ["risk_analytics", "verification"]},
    {"agent_id": "vit-sentiment-agent", "name": "Sentiment Analytics Agent", "capabilities": ["sentiment", "data_processing"]},
    {"agent_id": "vit-governance-ai", "name": "Governance AI Advisor", "capabilities": ["governance", "general"]},
]


def _did_from_agent_id(agent_id: str) -> str:
    return f"did:vit:agent:{hashlib.sha3_256(agent_id.encode()).hexdigest()[:32]}"


async def bootstrap_agent_registry(db: AsyncSession) -> int:
    created = 0
    with db.no_autoflush:
        for cfg in BUILTIN_AGENTS:
            existing = await db.scalar(
                select(AIAgentRegistration).where(AIAgentRegistration.agent_id == cfg["agent_id"])
            )
            if not existing:
                did = _did_from_agent_id(cfg["agent_id"])
                agent = AIAgentRegistration(
                    agent_id=cfg["agent_id"],
                    name=cfg["name"],
                    capabilities=json.dumps(cfg["capabilities"]),
                    did_identifier=did,
                    status=AgentStatus.ACTIVE,
                    is_builtin=True,
                    reputation_score=Decimal("75"),
                )
                db.add(agent)
                created += 1
    if created:
        await db.commit()
    return created


async def register_agent(
    db: AsyncSession,
    agent_id: str,
    name: str,
    capabilities: list[str],
    description: str | None = None,
    owner_user_id: int | None = None,
    endpoint_url: str | None = None,
    public_key: str | None = None,
    initial_stake: Decimal = Decimal("0"),
) -> AIAgentRegistration:
    existing = await db.scalar(
        select(AIAgentRegistration).where(AIAgentRegistration.agent_id == agent_id)
    )
    if existing:
        raise ValueError(f"Agent {agent_id} already registered")

    did = _did_from_agent_id(agent_id)
    agent = AIAgentRegistration(
        agent_id=agent_id,
        name=name,
        description=description,
        owner_user_id=owner_user_id,
        capabilities=json.dumps(capabilities),
        did_identifier=did,
        endpoint_url=endpoint_url,
        public_key=public_key,
        stake_amount=initial_stake,
        status=AgentStatus.PENDING,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def activate_agent(db: AsyncSession, agent_id: str) -> AIAgentRegistration:
    agent = await db.scalar(
        select(AIAgentRegistration).where(AIAgentRegistration.agent_id == agent_id)
    )
    if not agent:
        raise ValueError("Agent not found")
    agent.status = AgentStatus.ACTIVE
    await db.commit()
    await db.refresh(agent)
    return agent


async def record_agent_task(
    db: AsyncSession,
    agent_id: str,
    task_type: str,
    success: bool,
    latency_ms: int | None = None,
    accuracy: float | None = None,
    vit_earned: Decimal = Decimal("0"),
    task_ref: str | None = None,
    notes: str | None = None,
) -> AgentPerformanceRecord:
    agent = await db.scalar(
        select(AIAgentRegistration).where(AIAgentRegistration.agent_id == agent_id)
    )
    if not agent:
        raise ValueError("Agent not found")

    proof_hash = "0x" + hashlib.sha3_256(
        f"{agent_id}:{task_type}:{task_ref}:{secrets.token_hex(8)}".encode()
    ).hexdigest()

    record = AgentPerformanceRecord(
        agent_id=agent.id,
        task_type=task_type,
        task_ref=task_ref,
        success=success,
        latency_ms=latency_ms,
        accuracy=Decimal(str(accuracy)) if accuracy is not None else None,
        vit_earned=vit_earned,
        proof_hash=proof_hash,
        notes=notes,
    )
    db.add(record)

    agent.total_tasks += 1
    if success:
        agent.successful_tasks += 1
    else:
        agent.failed_tasks += 1
    agent.total_earned_vit += vit_earned
    agent.last_active_at = datetime.now(timezone.utc)

    if agent.total_tasks > 0:
        agent.accuracy_rate = Decimal(str(agent.successful_tasks / agent.total_tasks))

    total_rep = float(agent.reputation_score)
    delta = 2.0 if success else -5.0
    agent.reputation_score = Decimal(str(max(0.0, min(100.0, total_rep + delta))))

    await db.commit()
    await db.refresh(record)
    return record


async def issue_credential(
    db: AsyncSession,
    agent_id: str,
    credential_type: str,
    issued_by: str | None = None,
    valid_days: int = 365,
) -> AgentCredential:
    agent = await db.scalar(
        select(AIAgentRegistration).where(AIAgentRegistration.agent_id == agent_id)
    )
    if not agent:
        raise ValueError("Agent not found")

    cred_hash = "0x" + hashlib.sha3_256(
        f"{agent_id}:{credential_type}:{issued_by}:{secrets.token_hex(8)}".encode()
    ).hexdigest()

    from datetime import timedelta
    cred = AgentCredential(
        agent_id=agent.id,
        credential_type=credential_type,
        credential_hash=cred_hash,
        issued_by=issued_by,
        status=CredentialStatus.VALID,
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=valid_days),
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return cred


async def add_payment_route(
    db: AsyncSession,
    agent_id: str,
    route_type: str,
    recipient_address: str,
    split_pct: Decimal = Decimal("100"),
) -> AgentPaymentRoute:
    agent = await db.scalar(
        select(AIAgentRegistration).where(AIAgentRegistration.agent_id == agent_id)
    )
    if not agent:
        raise ValueError("Agent not found")

    route = AgentPaymentRoute(
        agent_id=agent.id,
        route_type=route_type,
        recipient_address=recipient_address,
        split_pct=split_pct,
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return route


async def get_agent_stats(db: AsyncSession) -> dict:
    total = await db.scalar(select(func.count(AIAgentRegistration.id))) or 0
    active = await db.scalar(
        select(func.count(AIAgentRegistration.id)).where(
            AIAgentRegistration.status == AgentStatus.ACTIVE
        )
    ) or 0
    total_tasks = await db.scalar(select(func.sum(AIAgentRegistration.total_tasks))) or 0
    total_earned = await db.scalar(select(func.sum(AIAgentRegistration.total_earned_vit))) or 0
    avg_rep = await db.scalar(select(func.avg(AIAgentRegistration.reputation_score))) or 0
    return {
        "total_agents": total,
        "active_agents": active,
        "total_tasks_processed": total_tasks,
        "total_vit_earned": float(total_earned),
        "average_reputation": float(avg_rep),
    }


async def list_agents(
    db: AsyncSession,
    status: AgentStatus | None = None,
    limit: int = 50,
) -> list[AIAgentRegistration]:
    q = select(AIAgentRegistration)
    if status:
        q = q.where(AIAgentRegistration.status == status)
    q = q.order_by(AIAgentRegistration.reputation_score.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())
