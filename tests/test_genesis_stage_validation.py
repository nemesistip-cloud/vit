import pytest

from app.api.routes.genesis import GENESIS_STATE_KEY, TOTAL_STAGES, _read_genesis_state, _validate_stage
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
    assert empty_models["reason"] == "Model registry has insufficient metadata"
    assert empty_active_models["reason"] == "AI registry or gateway URL is not ready"

    db_session.add(TreasuryPool(pool_type=PoolType.RESERVE))
    db_session.add_all(
        ModelMetadata(key=f"genesis-model-{index}", name=f"Model {index}", model_type="test", is_active=True)
        for index in range(3)
    )
    await db_session.commit()
    monkeypatch.setenv("VIT_AI_URL", "https://ai.example.test")

    assert (await _validate_stage(db_session, 6))["passed"] is True
    assert (await _validate_stage(db_session, 7))["passed"] is True
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
