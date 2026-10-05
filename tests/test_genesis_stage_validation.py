import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.routes.genesis import (
    LEGACY_MINT_CONFIRMATION,
    GENESIS_STATE_KEY,
    TOTAL_STAGES,
    LegacyMintAcceptanceRequest,
    GenesisAdvanceRequest,
    _persist_genesis_state,
    _read_genesis_state,
    _validate_stage,
    accept_existing_genesis_mint,
    advance_genesis_stage,
)
from app.modules.ai.models import ModelMetadata
from app.db.models import AuditLog, User
from app.services.vit_chain_client import VitChainClient
from app.modules.treasury.models import PoolType, TreasuryPool
from app.modules.wallet.models import PlatformConfig


@pytest.mark.asyncio
async def test_genesis_treasury_and_ai_stages_use_database_counts(db_session, monkeypatch):
    async def mock_evidence():
        return {
            "chain_id": "7764",
            "genesis_height": 0,
            "block_hash": "0x123",
            "transaction_hash": "0x456",
            "recipient_address": "VIT123",
            "amount": "1000000",
            "transaction_signature_present": True,
            "validator_signature_present": True,
        }
    monkeypatch.setattr("app.api.routes.genesis._legacy_genesis_evidence", mock_evidence)
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
        "reason": "An existing 1,000,000 VIT genesis mint was found; explicit super-admin legacy acceptance is required",
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
    assert stage_seven["reason"] == "An existing 1,000,000 VIT genesis mint was found; explicit super-admin legacy acceptance is required"
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


@pytest.mark.asyncio
async def test_stage_seven_accepts_only_matching_audited_legacy_mint(db_session, monkeypatch):
    evidence = {
        "chain_id": 7764,
        "chain_height": 28138,
        "genesis_height": 0,
        "block_hash": "0x" + "a" * 64,
        "transaction_hash": "0x" + "b" * 64,
        "recipient_address": "0x" + "c" * 40,
        "amount": "1000000",
        "total_supply": "1281390",
        "transaction_signature_present": False,
        "validator_signature_present": True,
    }
    block = {
        "height": 0,
        "block_hash": evidence["block_hash"],
        "validator_signature": "0x" + "d" * 130,
        "transactions": [{
            "tx_hash": evidence["transaction_hash"],
            "from_address": "0x" + "0" * 40,
            "to_address": evidence["recipient_address"],
            "amount": "1000000",
            "signature": "",
            "data": {"type": "genesis_mint"},
        }],
    }

    async def chain_status(self):
        return {"chain_id": 7764, "block_height": 28138}

    async def genesis_block(self, height):
        return block

    async def chain_supply(self):
        return {"total_supply": "1281390"}

    monkeypatch.setattr(VitChainClient, "status", chain_status)
    monkeypatch.setattr(VitChainClient, "block", genesis_block)
    monkeypatch.setattr(VitChainClient, "supply", chain_supply)

    no_exception = await _validate_stage(db_session, 7)
    assert no_exception["passed"] is False

    db_session.add(PlatformConfig(
        key="genesis_legacy_mint_acceptance",
        value={
            "accepted": True,
            "exception_type": "legacy_genesis_without_multisig_evidence",
            "accepted_by": 42,
            "reason": "Authorized legacy genesis acceptance; no second mint will be performed.",
            "evidence": evidence,
        },
    ))
    await db_session.commit()

    accepted = await _validate_stage(db_session, 7)
    assert accepted["passed"] is True
    assert "2-of-3 signer evidence is not claimed" in accepted["reason"]

    block["block_hash"] = "0x" + "e" * 64
    changed_chain = await _validate_stage(db_session, 7)
    assert changed_chain["passed"] is False


@pytest.mark.asyncio
async def test_legacy_mint_acceptance_is_super_admin_attributed_and_audited(db_session, monkeypatch):
    evidence = {
        "chain_id": 7764,
        "chain_height": 28138,
        "genesis_height": 0,
        "block_hash": "0x" + "a" * 64,
        "transaction_hash": "0x" + "b" * 64,
        "recipient_address": "0x" + "c" * 40,
        "amount": "1000000",
        "total_supply": "1281390",
        "transaction_signature_present": False,
        "validator_signature_present": True,
    }
    block = {
        "height": 0,
        "block_hash": evidence["block_hash"],
        "validator_signature": "0x" + "d" * 130,
        "transactions": [{
            "tx_hash": evidence["transaction_hash"],
            "from_address": "0x" + "0" * 40,
            "to_address": evidence["recipient_address"],
            "amount": "1000000",
            "signature": "",
            "data": {"type": "genesis_mint"},
        }],
    }

    async def chain_status(self):
        return {"chain_id": 7764, "block_height": 28138}

    async def genesis_block(self, height):
        return block

    async def chain_supply(self):
        return {"total_supply": "1281390"}

    monkeypatch.setattr(VitChainClient, "status", chain_status)
    monkeypatch.setattr(VitChainClient, "block", genesis_block)
    monkeypatch.setattr(VitChainClient, "supply", chain_supply)

    admin = User(id=42, email="superadmin@example.test", username="superadmin", role="super_admin")
    db_session.add(admin)
    db_session.add(PlatformConfig(
        key=GENESIS_STATE_KEY,
        value={"current_stage": 7, "completed_stages": list(range(1, 7))},
    ))
    await db_session.commit()

    result = await accept_existing_genesis_mint(
        LegacyMintAcceptanceRequest(
            confirmation=LEGACY_MINT_CONFIRMATION,
            reason="Authorized legacy acceptance; no verified 2-of-3 evidence and no new mint.",
        ),
        db_session,
        admin,
    )

    assert result["accepted"] is True
    assert result["new_mint_submitted"] is False
    assert result["two_of_three_signer_evidence_verified"] is False
    stored = await db_session.scalar(
        select(PlatformConfig).where(PlatformConfig.key == "genesis_legacy_mint_acceptance")
    )
    audit = await db_session.scalar(
        select(AuditLog).where(AuditLog.action == "genesis.legacy_mint.accepted")
    )
    assert stored.value["accepted_by"] == admin.id
    assert stored.value["evidence"] == evidence
    assert audit.actor == str(admin.id)
    assert audit.status == "warning"
