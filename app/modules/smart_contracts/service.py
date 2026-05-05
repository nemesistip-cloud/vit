"""Smart Contract Service — deploy, call, and query contracts."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.smart_contracts.executor import (
    BUILTIN_ABIS,
    BUILTIN_RULES,
    execute_contract_call,
)
from app.modules.smart_contracts.models import (
    CallStatus,
    ContractCall,
    ContractEvent,
    ContractStatus,
    ContractUpgrade,
    SmartContract,
)

logger = logging.getLogger(__name__)

BUILTIN_CONTRACTS = list(BUILTIN_ABIS.keys())


def _contract_address(name: str) -> str:
    seed = f"vit:{name}:v1".encode()
    return "0x" + hashlib.sha3_256(seed).hexdigest()[:40]


async def bootstrap_builtin_contracts(db: AsyncSession) -> int:
    """Deploy built-in contracts if they don't exist. Returns count created."""
    created = 0
    for name in BUILTIN_CONTRACTS:
        addr = _contract_address(name)
        existing = await db.scalar(
            select(SmartContract).where(SmartContract.address == addr)
        )
        if not existing:
            contract = SmartContract(
                name=name,
                address=addr,
                abi=BUILTIN_ABIS[name],
                rules={k: str(v) if isinstance(v, Decimal) else v
                       for k, v in BUILTIN_RULES.get(name, {}).items()},
                state={"initialized_at": datetime.utcnow().isoformat()},
                is_builtin=True,
                description=f"VIT built-in {name} contract",
                version="1.0.0",
            )
            db.add(contract)
            created += 1
    if created:
        await db.commit()
    return created


async def deploy_contract(
    db: AsyncSession,
    name: str,
    abi: list[dict],
    rules: dict,
    initial_state: dict,
    description: str | None = None,
    deployer_user_id: int | None = None,
) -> SmartContract:
    existing = await db.scalar(
        select(SmartContract).where(SmartContract.name == name)
    )
    if existing:
        raise ValueError(f"Contract '{name}' already deployed at {existing.address}")

    address = "0x" + hashlib.sha3_256(
        f"{name}:{secrets.token_hex(16)}:{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:40]

    contract = SmartContract(
        name=name,
        address=address,
        abi=abi,
        rules=rules,
        state=initial_state,
        description=description,
        deployer_user_id=deployer_user_id,
        is_builtin=False,
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


async def call_contract(
    db: AsyncSession,
    contract_address: str,
    method: str,
    params: dict,
    caller_user_id: int | None = None,
    current_block: int = 0,
) -> dict[str, Any]:
    contract = await db.scalar(
        select(SmartContract).where(SmartContract.address == contract_address)
    )
    if not contract:
        return {"success": False, "error": "Contract not found", "gas_used": 0}
    if contract.status != ContractStatus.ACTIVE:
        return {"success": False, "error": f"Contract is {contract.status}", "gas_used": 0}
    if contract.total_gas_used + GAS_FOR_DEFAULT > contract.gas_limit * 10_000:
        return {"success": False, "error": "Contract gas exhausted", "gas_used": 0}

    caller_str = str(caller_user_id) if caller_user_id else "anonymous"

    execution = execute_contract_call(
        contract_address=contract.address,
        contract_name=contract.name,
        method=method,
        params=params,
        state=dict(contract.state),
        rules=dict(contract.rules),
        caller=caller_str,
        block_number=current_block,
    )

    call_status = CallStatus.SUCCESS if execution["success"] else CallStatus.REVERTED

    call_record = ContractCall(
        contract_id=contract.id,
        caller_user_id=caller_user_id,
        method=method,
        params=params,
        result=execution.get("result"),
        status=call_status,
        gas_used=execution["gas_used"],
        error_message=execution.get("error"),
        tx_hash=execution["tx_hash"],
        block_number=current_block,
    )
    db.add(call_record)

    if execution["success"]:
        contract.state = execution["new_state"]
        contract.total_calls += 1
        contract.total_gas_used += execution["gas_used"]

    await db.flush()

    for i, evt in enumerate(execution.get("events", [])):
        event_record = ContractEvent(
            contract_id=contract.id,
            call_id=call_record.id,
            event_name=evt["name"],
            topic=evt["topic"],
            data=evt["data"],
            log_index=i,
            block_number=current_block,
        )
        db.add(event_record)

    await db.commit()
    return execution


GAS_FOR_DEFAULT = 30_000


async def get_contract(db: AsyncSession, address: str) -> SmartContract | None:
    return await db.scalar(
        select(SmartContract).where(SmartContract.address == address)
    )


async def get_contract_by_name(db: AsyncSession, name: str) -> SmartContract | None:
    return await db.scalar(
        select(SmartContract).where(SmartContract.name == name)
    )


async def list_contracts(db: AsyncSession, include_builtin: bool = True) -> list[SmartContract]:
    q = select(SmartContract)
    if not include_builtin:
        q = q.where(SmartContract.is_builtin.is_(False))
    result = await db.execute(q.order_by(SmartContract.deployed_at.desc()))
    return list(result.scalars().all())


async def get_contract_events(
    db: AsyncSession, contract_address: str, limit: int = 50
) -> list[ContractEvent]:
    contract = await get_contract(db, contract_address)
    if not contract:
        return []
    result = await db.execute(
        select(ContractEvent)
        .where(ContractEvent.contract_id == contract.id)
        .order_by(ContractEvent.emitted_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_call_history(
    db: AsyncSession, contract_address: str, limit: int = 50
) -> list[ContractCall]:
    contract = await get_contract(db, contract_address)
    if not contract:
        return []
    result = await db.execute(
        select(ContractCall)
        .where(ContractCall.contract_id == contract.id)
        .order_by(ContractCall.called_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def upgrade_contract(
    db: AsyncSession,
    contract_address: str,
    new_abi: list[dict],
    new_rules: dict,
    to_version: str,
    proposer_user_id: int | None = None,
    migration_notes: str | None = None,
) -> ContractUpgrade:
    contract = await get_contract(db, contract_address)
    if not contract:
        raise ValueError("Contract not found")

    upgrade = ContractUpgrade(
        contract_id=contract.id,
        from_version=contract.version,
        to_version=to_version,
        proposed_by=proposer_user_id,
        new_abi=new_abi,
        new_rules=new_rules,
        migration_notes=migration_notes,
    )
    db.add(upgrade)
    await db.commit()
    await db.refresh(upgrade)
    return upgrade


async def execute_upgrade(db: AsyncSession, upgrade_id: int) -> SmartContract:
    upgrade = await db.get(ContractUpgrade, upgrade_id)
    if not upgrade:
        raise ValueError("Upgrade not found")
    if upgrade.executed:
        raise ValueError("Upgrade already executed")

    contract = await db.get(SmartContract, upgrade.contract_id)
    if not contract:
        raise ValueError("Contract not found")

    contract.abi = upgrade.new_abi
    contract.rules = upgrade.new_rules
    contract.version = upgrade.to_version
    contract.updated_at = datetime.utcnow()
    upgrade.approved = True
    upgrade.executed = True
    upgrade.executed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(contract)
    return contract
