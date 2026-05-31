"""Smart Contract Routes — deploy, call, query, upgrade contracts."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.smart_contracts.service import (
    bootstrap_builtin_contracts,
    call_contract,
    deploy_contract,
    execute_upgrade,
    get_call_history,
    get_contract,
    get_contract_by_name,
    get_contract_events,
    list_contracts,
    upgrade_contract,
)

router = APIRouter(prefix="/api/contracts", tags=["smart-contracts"])


class DeployRequest(BaseModel):
    name: str
    abi: list[dict] = Field(default_factory=list)
    rules: dict = Field(default_factory=dict)
    initial_state: dict = Field(default_factory=dict)
    description: Optional[str] = None


class CallRequest(BaseModel):
    method: str
    params: dict = Field(default_factory=dict)
    caller_user_id: Optional[int] = None
    block_number: int = 0


class UpgradeRequest(BaseModel):
    new_abi: list[dict]
    new_rules: dict
    to_version: str
    proposer_user_id: Optional[int] = None
    migration_notes: Optional[str] = None


@router.post("/bootstrap")
async def bootstrap_contracts(db: AsyncSession = Depends(get_db)):
    count = await bootstrap_builtin_contracts(db)
    return {"created": count, "message": f"Bootstrapped {count} built-in contracts"}


@router.get("")
async def list_all_contracts(
    include_builtin: bool = True,
    db: AsyncSession = Depends(get_db),
):
    contracts = await list_contracts(db, include_builtin=include_builtin)
    return {
        "contracts": [
            {
                "address": c.address,
                "name": c.name,
                "version": c.version,
                "status": c.status.value,
                "is_builtin": c.is_builtin,
                "total_calls": c.total_calls,
                "total_gas_used": c.total_gas_used,
                "vit_locked": float(c.vit_locked),
                "deployed_at": c.deployed_at.isoformat(),
                "abi_methods": [m["name"] for m in c.abi] if isinstance(c.abi, list) else [],
            }
            for c in contracts
        ],
        "total": len(contracts),
    }


@router.post("/deploy")
async def deploy_new_contract(
    req: DeployRequest,
    deployer_user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        contract = await deploy_contract(
            db,
            name=req.name,
            abi=req.abi,
            rules=req.rules,
            initial_state=req.initial_state,
            description=req.description,
            deployer_user_id=deployer_user_id,
        )
        return {
            "address": contract.address,
            "name": contract.name,
            "version": contract.version,
            "deployed_at": contract.deployed_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{address}")
async def get_contract_info(address: str, db: AsyncSession = Depends(get_db)):
    contract = await get_contract(db, address)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return {
        "address": contract.address,
        "name": contract.name,
        "symbol": contract.symbol,
        "version": contract.version,
        "status": contract.status.value,
        "is_builtin": contract.is_builtin,
        "abi": contract.abi,
        "rules": contract.rules,
        "state": contract.state,
        "gas_limit": contract.gas_limit,
        "total_calls": contract.total_calls,
        "total_gas_used": contract.total_gas_used,
        "vit_locked": float(contract.vit_locked),
        "description": contract.description,
        "deployed_at": contract.deployed_at.isoformat(),
    }


@router.post("/{address}/call")
async def call_contract_method(
    address: str,
    req: CallRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await call_contract(
        db,
        contract_address=address,
        method=req.method,
        params=req.params,
        caller_user_id=req.caller_user_id,
        current_block=req.block_number,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Execution reverted"))
    return result


@router.get("/{address}/events")
async def get_events(
    address: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    events = await get_contract_events(db, address, limit=limit)
    return {
        "events": [
            {
                "id": e.id,
                "event_name": e.event_name,
                "topic": e.topic,
                "data": e.data,
                "log_index": e.log_index,
                "block_number": e.block_number,
                "emitted_at": e.emitted_at.isoformat(),
            }
            for e in events
        ]
    }


@router.get("/{address}/calls")
async def get_calls(
    address: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    calls = await get_call_history(db, address, limit=limit)
    return {
        "calls": [
            {
                "id": c.id,
                "method": c.method,
                "params": c.params,
                "result": c.result,
                "status": c.status.value,
                "gas_used": c.gas_used,
                "tx_hash": c.tx_hash,
                "block_number": c.block_number,
                "error": c.error_message,
                "called_at": c.called_at.isoformat(),
            }
            for c in calls
        ]
    }


@router.post("/{address}/upgrade")
async def propose_upgrade(
    address: str,
    req: UpgradeRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        upgrade = await upgrade_contract(
            db,
            contract_address=address,
            new_abi=req.new_abi,
            new_rules=req.new_rules,
            to_version=req.to_version,
            proposer_user_id=req.proposer_user_id,
            migration_notes=req.migration_notes,
        )
        return {
            "upgrade_id": upgrade.id,
            "from_version": upgrade.from_version,
            "to_version": upgrade.to_version,
            "proposed_at": upgrade.proposed_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upgrades/{upgrade_id}/execute")
async def execute_contract_upgrade(upgrade_id: int, db: AsyncSession = Depends(get_db)):
    try:
        contract = await execute_upgrade(db, upgrade_id)
        return {"address": contract.address, "version": contract.version, "message": "Upgrade executed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/by-name/{name}")
async def get_by_name(name: str, db: AsyncSession = Depends(get_db)):
    contract = await get_contract_by_name(db, name)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return {"address": contract.address, "name": contract.name, "version": contract.version, "status": contract.status.value}
