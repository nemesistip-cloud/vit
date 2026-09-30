import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.admin import require_admin
from app.db.database import get_db
from app.modules.wallet.models import PlatformConfig

router = APIRouter(prefix="/genesis", tags=["Genesis"])

GENESIS_STATE_KEY = "genesis_initialization_state"
TOTAL_STAGES = 10


class GenesisAdvanceRequest(BaseModel):
    stage: Optional[int] = None


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
        str(stage): validation_results.get(str(stage), {"stage": int(stage), "passed": False, "reason": "Validation not run"})
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
            from app.modules.ai.models import ModelMetadata
            count = await db.scalar(select(func.count()).select_from(ModelMetadata)) or 0
            passed = count >= 3
            summary = {"stage": 7, "passed": passed, "reason": "Model registry has insufficient metadata" if not passed else "Model registry metadata is initialized"}
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
    normalized_completed = sorted(normalized_completed)
    if current not in normalized_completed:
        normalized_completed.append(current)
    normalized_completed = sorted(set(normalized_completed))

    deps = await _runtime_dependencies_ok(db)
    validation_results = state.get("validation_results") or {}
    for stage in range(1, TOTAL_STAGES + 1):
        validation_results.setdefault(str(stage), await _validate_stage(db, stage))
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
    if state.get("updated_at") is None or state.get("status") == "bootstrapping":
        state = await _persist_genesis_state(db, state)
    return state


@router.get("/validate/{stage}")
async def validate_genesis_stage(stage: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await _validate_stage(db, stage)


@router.post("/advance")
async def advance_genesis_stage(
    request: GenesisAdvanceRequest,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
) -> Dict[str, Any]:
    state = await _read_genesis_state(db)
    target_stage = request.stage if request.stage is not None else state["current_stage"] + 1
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
