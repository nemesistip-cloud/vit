import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.admin import require_admin, require_super_admin
from app.db.database import get_db
from app.db.models import AuditLog, User
from app.modules.wallet.models import PlatformConfig
from app.services.vit_chain_client import VitChainClient, VitChainClientError

router = APIRouter(prefix="/genesis", tags=["Genesis"])

GENESIS_STATE_KEY = "genesis_initialization_state"
LEGACY_MINT_ACCEPTANCE_KEY = "genesis_legacy_mint_acceptance"
LEGACY_MINT_CONFIRMATION = "ACCEPT EXISTING GENESIS MINT"
GENESIS_MINT_AMOUNT = Decimal("1000000")
MAX_VIT_SUPPLY = Decimal("10000000")
TOTAL_STAGES = 10


class GenesisAdvanceRequest(BaseModel):
    stage: Optional[int] = None


class LegacyMintAcceptanceRequest(BaseModel):
    confirmation: str
    reason: str


async def _read_genesis_state(db: AsyncSession) -> Dict[str, Any]:
    row = (
        await db.execute(
            select(PlatformConfig).where(PlatformConfig.key == GENESIS_STATE_KEY)
        )
    ).scalar_one_or_none()

    if row and isinstance(row.value, dict):
        payload = dict(row.value)
    else:
        payload = {}

    current_stage = int(payload.get("current_stage", 1) or 1)
    completed = payload.get("completed_stages", []) or []
    normalized_completed = []
    seen = set()
    for stage in completed:
        try:
            stage_id = int(stage)
        except (TypeError, ValueError):
            continue
        if not 1 <= stage_id <= TOTAL_STAGES:
            continue
        if stage_id not in seen:
            normalized_completed.append(stage_id)
            seen.add(stage_id)
    normalized_completed = sorted(normalized_completed)

    dependency_status = payload.get("dependency_status") or {"database": False, "redis": False}
    validation_results = payload.get("validation_results") or {}
    validation_results = {
        str(stage): validation_results.get(
            str(stage),
            {"stage": stage, "passed": False, "reason": "Validation not run"},
        )
        for stage in range(1, TOTAL_STAGES + 1)
    }
    for stage in validation_results:
        validation_results[str(stage)] = validation_results[str(stage)]

    verified = (
        current_stage >= TOTAL_STAGES
        and bool(dependency_status.get("database"))
        and bool(dependency_status.get("redis"))
        and all(item.get("passed", False) for item in validation_results.values())
    )

    return {
        "current_stage": max(1, min(current_stage, TOTAL_STAGES)),
        "completed_stages": normalized_completed,
        "total_stages": TOTAL_STAGES,
        "parameters": payload.get("parameters") or {},
        "status": "verified" if verified else "bootstrapping",
        "verified": verified,
        "updated_at": payload.get("updated_at"),
        "dependency_status": {
            "database": bool(dependency_status.get("database")),
            "redis": bool(dependency_status.get("redis")),
        },
        "validation_results": validation_results,
    }


async def _runtime_dependencies_ok(db: AsyncSession) -> Dict[str, bool]:
    database_ok = False
    redis_ok = False

    try:
        await db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        database_ok = False

    try:
        from app.core.redis import redis_client as shared_redis_client
        if shared_redis_client is not None:
            await shared_redis_client.ping()
            redis_ok = True
    except Exception:
        redis_ok = False

    return {"database": database_ok, "redis": redis_ok}


async def _legacy_genesis_evidence() -> Dict[str, Any]:
    chain = VitChainClient()
    status, block, supply = await asyncio.gather(
        chain.status(),
        chain.block("0"),
        chain.supply(),
    )
    transactions = block.get("transactions")
    if not isinstance(transactions, list) or len(transactions) != 1:
        raise ValueError("Block 0 does not contain exactly one genesis transaction")
    transaction = transactions[0]

    try:
        chain_id = int(status.get("chain_id", 0))
        chain_height = int(status.get("block_height", -1))
        genesis_height = int(block.get("height", -1))
        mint_amount = Decimal(str(transaction.get("amount")))
        total_supply = Decimal(str(supply.get("total_supply")))
    except (IndexError, TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError("The live chain returned invalid genesis evidence") from exc

    transaction_data = transaction.get("data")
    if not isinstance(transaction_data, dict) or transaction_data.get("type") != "genesis_mint":
        raise ValueError("Block 0 does not contain a genesis_mint transaction")
    if chain_id != 7764 or genesis_height != 0 or chain_height < 1:
        raise ValueError("The live chain identity or height does not match the legacy genesis")
    if mint_amount != GENESIS_MINT_AMOUNT or total_supply < mint_amount or total_supply > MAX_VIT_SUPPLY:
        raise ValueError("The live genesis amount or total supply is outside the approved limits")

    block_hash = str(block.get("block_hash") or block.get("hash") or "")
    transaction_hash = str(transaction.get("tx_hash") or transaction.get("hash") or "")
    recipient_address = str(transaction.get("to_address") or transaction.get("to") or "")
    sender = str(transaction.get("from_address") or transaction.get("from") or "").lower()
    zero_senders = {"0x" + "0" * 40, "vit" + "0" * 40}
    if not block_hash or not transaction_hash or not recipient_address or sender not in zero_senders:
        raise ValueError("The existing genesis transaction is missing required public evidence")

    return {
        "chain_id": chain_id,
        "chain_height": chain_height,
        "genesis_height": genesis_height,
        "block_hash": block_hash,
        "transaction_hash": transaction_hash,
        "recipient_address": recipient_address,
        "amount": format(mint_amount.normalize(), "f"),
        "total_supply": format(total_supply.normalize(), "f"),
        "transaction_signature_present": bool(transaction.get("signature")),
        "validator_signature_present": bool(block.get("validator_signature")),
    }


def _legacy_mint_snapshot_matches(accepted: Dict[str, Any], current: Dict[str, Any]) -> bool:
    immutable_fields = (
        "chain_id",
        "genesis_height",
        "block_hash",
        "transaction_hash",
        "recipient_address",
        "amount",
        "transaction_signature_present",
        "validator_signature_present",
    )
    return all(accepted.get(field) == current.get(field) for field in immutable_fields)


async def _validate_legacy_genesis_acceptance(db: AsyncSession) -> Dict[str, Any]:
    try:
        evidence = await _legacy_genesis_evidence()
    except (VitChainClientError, ValueError) as exc:
        return {
            "stage": 7,
            "passed": False,
            "reason": f"Existing genesis mint evidence could not be verified: {type(exc).__name__}",
        }

    row = await db.scalar(
        select(PlatformConfig).where(PlatformConfig.key == LEGACY_MINT_ACCEPTANCE_KEY)
    )
    acceptance = row.value if row and isinstance(row.value, dict) else None
    if not acceptance or acceptance.get("accepted") is not True:
        return {
            "stage": 7,
            "passed": False,
            "reason": "An existing 1,000,000 VIT genesis mint was found; explicit super-admin legacy acceptance is required",
        }

    accepted_evidence = acceptance.get("evidence")
    if not isinstance(accepted_evidence, dict) or not _legacy_mint_snapshot_matches(accepted_evidence, evidence):
        return {
            "stage": 7,
            "passed": False,
            "reason": "The accepted legacy genesis snapshot no longer matches block 0",
        }

    return {
        "stage": 7,
        "passed": True,
        "reason": "Existing genesis accepted under a super-admin legacy exception; 2-of-3 signer evidence is not claimed",
    }


async def _validate_stage(db: AsyncSession, stage: int) -> Dict[str, Any]:
    stage = max(1, min(int(stage), TOTAL_STAGES))
    summary: Dict[str, Any] = {"stage": stage, "passed": False, "reason": "Validation not run"}

    try:
        if stage == 1:
            currency = (os.getenv("SYSTEM_CURRENCY_BASE") or "USD").strip()
            rate_limit = int(os.getenv("RATE_LIMIT_MARGINS", "2000") or "2000")
            passed = bool(currency) and 100 <= rate_limit <= 100000
            summary = {"stage": 1, "passed": passed, "reason": "SYSTEM_CURRENCY_BASE is missing or RATE_LIMIT_MARGINS is outside 100-100000" if not passed else "Platform runtime configuration is valid"}
        elif stage == 2:
            resolver = (os.getenv("DID_RESOLVER_ENDPOINT") or "").strip()
            schema = (os.getenv("VALIDATOR_DID_SCHEMA") or "").strip()
            passed = bool(resolver) and bool(schema)
            summary = {"stage": 2, "passed": passed, "reason": "DID resolver endpoint and validator schema must be configured" if not passed else "Identity configuration is valid"}
        elif stage == 3:
            quorum = float(os.getenv("QUORUM_THRESHOLD_PERCENT", "20") or "20")
            voting_window = int(os.getenv("VOTING_WINDOW_SECONDS", "604800") or "604800")
            passed = 10 <= quorum <= 100 and voting_window >= 86400
            summary = {"stage": 3, "passed": passed, "reason": "Voting quorum or window is outside the governance contract" if not passed else "Governance configuration is valid"}
        elif stage == 4:
            chain_id = int(os.getenv("VIT_CHAIN_ID", "7764") or "7764")
            block_time = int(os.getenv("TARGET_BLOCK_TIME_SECONDS", "15") or "15")
            passed = chain_id in {7764, 0x1e54} and 5 <= block_time <= 60
            summary = {"stage": 4, "passed": passed, "reason": "VIT Chain ID or target block time is outside the approved range" if not passed else "Blockchain configuration is valid"}
        elif stage == 5:
            burn = float(os.getenv("GAS_FEE_BURN_PERCENT", "50") or "50")
            treasury = float(os.getenv("TREASURY_FEE_SHARE_PERCENT", "50") or "50")
            passed = abs((burn + treasury) - 100.0) < 1e-9
            summary = {"stage": 5, "passed": passed, "reason": "Fee shares must sum to exactly 100%" if not passed else "Wallet fee routing is valid"}
        elif stage == 6:
            from app.modules.treasury.models import TreasuryPool
            count = await db.scalar(select(func.count()).select_from(TreasuryPool)) or 0
            passed = count > 0
            summary = {"stage": 6, "passed": passed, "reason": "Treasury pools have not been bootstrapped" if not passed else "Genesis treasury is initialized"}
        elif stage == 7:
            summary = await _validate_legacy_genesis_acceptance(db)
        elif stage == 8:
            from app.modules.ai.models import ModelMetadata
            active_count = await db.scalar(
                select(func.count()).select_from(ModelMetadata).where(ModelMetadata.is_active.is_(True))
            ) or 0
            ai_base = (os.getenv("VIT_AI_URL") or "").strip()
            passed = active_count >= 3 and bool(ai_base)
            summary = {"stage": 8, "passed": passed, "reason": "AI registry or gateway URL is not ready" if not passed else "AI services are initialized"}
        elif stage == 9:
            try:
                from tachyon.core.providers.pool import ProviderPool
                provider_pool = ProviderPool()
                passed = len(provider_pool.providers) > 0
            except Exception:
                passed = False
            summary = {"stage": 9, "passed": passed, "reason": "No storage providers are available" if not passed else "Storage providers are initialized"}
        elif stage == 10:
            deps = await _runtime_dependencies_ok(db)
            passed = deps["database"] and deps["redis"]
            summary = {"stage": 10, "passed": passed, "reason": "Database or Redis is unavailable for final readiness verification" if not passed else "Mainnet readiness checks passed"}
        else:
            passed = False
            summary = {"stage": stage, "passed": False, "reason": " Unsupported genesis stage"}
    except Exception as exc:
        summary = {"stage": stage, "passed": False, "reason": f"Validation probe failed: {type(exc).__name__}"}

    return summary


async def _persist_genesis_state(db: AsyncSession, state: Dict[str, Any]) -> Dict[str, Any]:
    current = max(1, min(int(state.get("current_stage", 1) or 1), TOTAL_STAGES))
    completed = state.get("completed_stages") or []
    normalized_completed = []
    seen = set()
    for stage in completed:
        try:
            stage_id = int(stage)
        except (TypeError, ValueError):
            continue
        if 1 <= stage_id <= TOTAL_STAGES and stage_id not in seen:
            normalized_completed.append(stage_id)
            seen.add(stage_id)
    deps = await _runtime_dependencies_ok(db)
    validation_results = state.get("validation_results") or {}
    for stage in range(1, TOTAL_STAGES + 1):
        key = str(stage)
        result = validation_results.get(key)
        if not isinstance(result, dict) or "passed" not in result:
            validation_results[key] = await _validate_stage(db, stage)
    completed_set = set(normalized_completed)
    completed_set.add(current)
    normalized_completed = []
    for stage in range(1, current + 1):
        if stage not in completed_set or not validation_results[str(stage)]["passed"]:
            break
        normalized_completed.append(stage)
    verified = (
        current >= TOTAL_STAGES
        and deps["database"]
        and deps["redis"]
        and all(item.get("passed", False) for item in validation_results.values())
    )
    status = "verified" if verified else "bootstrapping"
    updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    payload = {
        "current_stage": current,
        "completed_stages": normalized_completed,
        "total_stages": TOTAL_STAGES,
        "parameters": state.get("parameters") or {},
        "status": status,
        "verified": verified,
        "updated_at": updated_at,
        "dependency_status": deps,
        "validation_results": validation_results,
    }

    row = (
        await db.execute(
            select(PlatformConfig).where(PlatformConfig.key == GENESIS_STATE_KEY)
        )
    ).scalar_one_or_none()

    if row:
        row.value = payload
        row.updated_by = getattr(row, "updated_by", None)
    else:
        db.add(PlatformConfig(key=GENESIS_STATE_KEY, value=payload, description="Genesis initialization lifecycle state"))

    await db.commit()
    return payload


@router.get("/status")
async def get_genesis_status(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    state = await _read_genesis_state(db)
    deps = await _runtime_dependencies_ok(db)
    validation_results = {
        str(stage): await _validate_stage(db, stage)
        for stage in range(1, TOTAL_STAGES + 1)
    }
    live_verified = bool(state.get("current_stage") >= TOTAL_STAGES and deps.get("database") and deps.get("redis") and all(item.get("passed", False) for item in validation_results.values()))
    state["verified"] = live_verified
    state["status"] = "verified" if state["verified"] else "bootstrapping"
    state["dependency_status"] = deps
    state["validation_results"] = validation_results
    return state


@router.get("/validate/{stage}")
async def validate_genesis_stage(stage: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await _validate_stage(db, stage)


@router.post("/accept-existing-mint")
async def accept_existing_genesis_mint(
    request: LegacyMintAcceptanceRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
) -> Dict[str, Any]:
    if request.confirmation != LEGACY_MINT_CONFIRMATION:
        raise HTTPException(status_code=400, detail="Confirmation text does not match")

    reason = request.reason.strip()
    if len(reason) < 40:
        raise HTTPException(status_code=400, detail="A reason of at least 40 characters is required")

    state = await _read_genesis_state(db)
    if state["current_stage"] != 7:
        raise HTTPException(status_code=409, detail="Legacy mint acceptance is only available at Stage 7")

    existing = await db.scalar(
        select(PlatformConfig).where(PlatformConfig.key == LEGACY_MINT_ACCEPTANCE_KEY)
    )
    if existing:
        raise HTTPException(status_code=409, detail="A legacy genesis acceptance is already recorded")

    try:
        evidence = await _legacy_genesis_evidence()
    except (VitChainClientError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Existing genesis evidence unavailable: {type(exc).__name__}") from exc

    accepted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    exception = {
        "accepted": True,
        "exception_type": "legacy_genesis_without_verified_multisig",
        "accepted_by": admin.id,
        "accepted_at": accepted_at,
        "reason": reason,
        "acknowledgements": {
            "existing_mint_will_not_be_repeated": True,
            "two_of_three_signer_evidence_verified": False,
            "treasury_operations_split_verified": False,
        },
        "evidence": evidence,
    }

    db.add(PlatformConfig(
        key=LEGACY_MINT_ACCEPTANCE_KEY,
        value=exception,
        description="Super-admin exception accepting the existing block-0 mint without verified 2-of-3 ceremony evidence",
        updated_by=admin.id,
    ))
    db.add(AuditLog(
        action="genesis.legacy_mint.accepted",
        actor=str(admin.id),
        resource="genesis",
        resource_id="legacy-block-0-mint",
        details=exception,
        ip_address=None,
        status="warning",
    ))
    await db.commit()

    return {
        "accepted": True,
        "stage": 7,
        "exception_type": exception["exception_type"],
        "evidence": evidence,
        "two_of_three_signer_evidence_verified": False,
        "new_mint_submitted": False,
    }


@router.post("/advance")
async def advance_genesis_stage(
    request: GenesisAdvanceRequest,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
) -> Dict[str, Any]:
    state = await _read_genesis_state(db)
    if state["current_stage"] >= TOTAL_STAGES:
        raise HTTPException(status_code=409, detail="Genesis is already at the final stage")

    next_stage = state["current_stage"] + 1
    if request.stage is not None and int(request.stage) != next_stage:
        raise HTTPException(status_code=409, detail="Genesis stages must be advanced sequentially")

    current_validation = await _validate_stage(db, state["current_stage"])
    if not current_validation["passed"]:
        raise HTTPException(
            status_code=400,
            detail={"stage": state["current_stage"], "validation": current_validation},
        )

    target_stage = request.stage if request.stage is not None else next_stage
    current_stage = max(1, min(int(target_stage), TOTAL_STAGES))

    validation = await _validate_stage(db, current_stage)
    if not validation["passed"]:
        raise HTTPException(status_code=400, detail={"stage": current_stage, "validation": validation})

    completed = set(state.get("completed_stages", []))
    completed.add(current_stage)

    deps = await _runtime_dependencies_ok(db)
    updated = {
        "current_stage": current_stage,
        "completed_stages": sorted(completed),
        "total_stages": TOTAL_STAGES,
        "verified": current_stage >= TOTAL_STAGES and deps["database"] and deps["redis"],
        "dependency_status": deps,
    }
    return await _persist_genesis_state(db, updated)


@router.post("/initialize-stage/{stage_num}")
async def initialize_stage(
    stage_num: int,
    payload: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
) -> Dict[str, Any]:
    if stage_num < 1 or stage_num > TOTAL_STAGES:
        raise HTTPException(status_code=400, detail="Invalid stage number")

    validation = await _validate_stage(db, stage_num)
    state = await _read_genesis_state(db)

    validation_results = state.get("validation_results") or {}
    validation_results[str(stage_num)] = validation

    completed = set(state.get("completed_stages") or [])
    if validation["passed"]:
        completed.add(stage_num)

    current_stage = state.get("current_stage", 1)
    if validation["passed"] and stage_num >= current_stage:
        current_stage = stage_num

    existing_params = dict(state.get("parameters") or {})
    if payload:
        existing_params.update(payload)

    deps = await _runtime_dependencies_ok(db)
    updated = {
        "current_stage": current_stage,
        "completed_stages": sorted(completed),
        "total_stages": TOTAL_STAGES,
        "parameters": existing_params,
        "validation_results": validation_results,
        "dependency_status": deps,
    }

    persisted = await _persist_genesis_state(db, updated)
    return {
        "status": "success",
        "stage": stage_num,
        "validation": validation,
        "genesis_state": persisted,
    }
