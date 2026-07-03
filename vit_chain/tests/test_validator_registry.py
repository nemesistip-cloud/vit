import pytest
from unittest.mock import AsyncMock, MagicMock
from vit_chain.consensus.registry import ValidatorRegistry
from vit_chain.consensus.models import Validator

@pytest.mark.asyncio
async def test_validator_registration():
    db = AsyncMock()
    registry = ValidatorRegistry()

    # Mock existing check
    db.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)

    node_id = "did:vit:agent:test-node"
    pub_key = "0x1234"

    validator = await registry.register(db, node_id, pub_key)

    assert validator.node_id == node_id
    assert validator.public_key == pub_key
    assert db.add.call_count == 2 # Validator and Reputation

@pytest.mark.asyncio
async def test_validator_jailing():
    db = AsyncMock()
    registry = ValidatorRegistry()

    node_id = "did:vit:agent:bad-node"
    await registry.jail_validator(db, node_id, reason="offline")

    db.execute.assert_called()
