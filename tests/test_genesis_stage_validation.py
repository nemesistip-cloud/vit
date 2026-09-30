import pytest
from fastapi import HTTPException

from app.api.routes.genesis import (
    GENESIS_STATE_KEY,
    TOTAL_STAGES,
    GenesisAdvanceRequest,
    _persist_genesis_state,
    _read_genesis_state,
    _validate_stage,
    advance_genesis_stage,
)
from app.modules.ai.models import ModelMetadata
from app.modules.treasury.models import PoolType, TreasuryPool
from app.modules.wallet.models import PlatformConfig


@pytest.mark.asyncio
async def test_genesis_treasury_and_ai_stages_use_database_counts(db_session, monkeypatch):
    empty_treasury = await _validate_stage(db_session, 6)
    empty_models = await _validate_stage(db_session, 7)
    empty_active_models = await _validate_stage(db_session, 8)

    assert empty_treasury == {
        "stage": 6,
        "passed": False,
        "reason": "Treasury pools have not been bootstrapped",
    }
    assert empty_models == {
        "stage": 7,
        "passed": False,
        "reason": "Genesis mint ceremony is not implemented; Stage 7 cannot be marked complete",
    }
    assert empty_active_models["reason"] == "AI registry or gateway URL is not ready"

    db_session.add(TreasuryPool(pool_type=PoolType.RESERVE))
    db_session.add_all(
        ModelMetadata(key=f"genesis-model-{index}", name=f"Model {index}", model_type="test", is_active=True)
        for index in range(3)
    )
    await db_session.commit()
    monkeypatch.setenv("VIT_AI_URL", "https://ai.example.test")

    assert (await _validate_stage(db_session, 6))["passed"] is True
    stage_seven = await _validate_stage(db_session, 7)
    assert stage_seven["passed"] is False
    assert stage_seven["reason"] == "Genesis mint ceremony is not implemented; Stage 7 cannot be marked complete"
    assert (await _validate_stage(db_session, 8))["passed"] is True


@pytest.mark.asyncio
async def test_stale_persisted_verified_flag_does_not_override_failed_stage(db_session):
    validations = {
        str(stage): {"stage": stage, "passed": True, "reason": "ready"}
        for stage in range(1, TOTAL_STAGES + 1)
    }
    validations["2"]["passed"] = False
    db_session.add(PlatformConfig(
        key=GENESIS_STATE_KEY,
        value={
            "current_stage": TOTAL_STAGES,
            "completed_stages": list(range(1, TOTAL_STAGES + 1)),
            "status": "verified",
            "verified": True,
            "dependency_status": {"database": True, "redis": True},
            "validation_results": validations,
        },
    ))
    await db_session.commit()

    state = await _read_genesis_state(db_session)

    assert state["verified"] is False
    assert state["status"] == "bootstrapping"


@pytest.mark.asyncio
async def test_genesis_advance_rejects_skipping_to_a_later_stage(db_session, monkeypatch):
    monkeypatch.setenv("VIT_AI_URL", "https://ai.example.test")
    db_session.add_all(
        ModelMetadata(key=f"skip-test-model-{index}", name=f"Model {index}", model_type="test", is_active=True)
        for index in range(3)
    )
    db_session.add(PlatformConfig(
        key=GENESIS_STATE_KEY,
        value={
            "current_stage": 6,
            "completed_stages": list(range(1, 7)),
            "verified": False,
            "dependency_status": {"database": True, "redis": True},
            "validation_results": {
                str(stage): {"stage": stage, "passed": stage != 7, "reason": "ready"}
                for stage in range(1, TOTAL_STAGES + 1)
            },
        },
    ))
    await db_session.commit()

    with pytest.raises(HTTPException) as error:
        await advance_genesis_stage(GenesisAdvanceRequest(stage=8), db_session, object())

    assert error.value.status_code == 409
    assert error.value.detail == "Genesis stages must be advanced sequentially"


@pytest.mark.asyncio
async def test_genesis_advance_cannot_leave_a_failed_current_stage(db_session, monkeypatch):
    monkeypatch.setenv("VIT_AI_URL", "https://ai.example.test")
    db_session.add_all(
        ModelMetadata(key=f"blocked-stage-model-{index}", name=f"Model {index}", model_type="test", is_active=True)
        for index in range(3)
    )
    db_session.add(PlatformConfig(
        key=GENESIS_STATE_KEY,
        value={
            "current_stage": 7,
            "completed_stages": list(range(1, 8)),
            "verified": False,
            "dependency_status": {"database": True, "redis": True},
            "validation_results": {
                str(stage): {"stage": stage, "passed": True, "reason": "ready"}
                for stage in range(1, TOTAL_STAGES + 1)
            },
        },
    ))
    await db_session.commit()

    with pytest.raises(HTTPException) as error:
        await advance_genesis_stage(GenesisAdvanceRequest(stage=8), db_session, object())

    assert error.value.status_code == 400
    assert error.value.detail["stage"] == 7


@pytest.mark.asyncio
async def test_persisted_completion_stops_before_failed_mint_stage(db_session, monkeypatch):
    monkeypatch.setenv("DID_RESOLVER_ENDPOINT", "https://did.example.test")
    monkeypatch.setenv("VALIDATOR_DID_SCHEMA", "W3C DID Core 1.0")
    db_session.add(TreasuryPool(pool_type=PoolType.RESERVE))
    await db_session.commit()

    state = await _persist_genesis_state(db_session, {
        "current_stage": 7,
        "completed_stages": list(range(1, 8)),
    })

    assert state["current_stage"] == 7
    assert state["completed_stages"] == list(range(1, 7))
    assert state["validation_results"]["7"]["passed"] is False
