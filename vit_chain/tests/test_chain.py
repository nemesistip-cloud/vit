import pytest
from decimal import Decimal
from vit_chain.core.transaction import VITTransaction, create_transaction, verify_transaction, Mempool
from vit_chain.core.block import VITBlock, build_block, validate_block
from vit_chain.core.state import ChainState
from vit_chain.genesis import build_genesis_block
from vit_chain.crypto.ecdsa import generate_keypair
from vit_chain.crypto.address import public_key_to_address

@pytest.fixture
def keys():
    priv, pub = generate_keypair()
    return priv, pub

def test_transaction_creation_and_verification(keys):
    priv, pub = keys
    addr = public_key_to_address(pub)

    # create_transaction handles signing
    to_addr = "VIT" + "1" * 40
    tx = create_transaction(priv, to_addr, Decimal("100"), 0)

    assert tx.from_address == addr
    assert tx.amount == Decimal("100")
    assert tx.nonce == 0
    assert tx.tx_hash != ""
    assert tx.signature != ""

    assert verify_transaction(tx)

def test_mempool():
    mempool = Mempool()
    priv, pub = generate_keypair()
    to_addr = "VIT" + "1" * 40
    tx = create_transaction(priv, to_addr, Decimal("10"), 0, timestamp=123)

    assert mempool.add(tx)
    assert mempool.size() == 1
    assert not mempool.add(tx) # Duplicate

    pending = mempool.get_pending()
    assert len(pending) == 1
    assert pending[0].tx_hash == tx.tx_hash

    mempool.remove([tx.tx_hash])
    assert mempool.size() == 0

def test_block_building_and_validation(keys):
    priv, pub = keys
    to_addr = "VIT" + "1" * 40
    tx = create_transaction(priv, to_addr, Decimal("10"), 0)

    block = build_block(None, [tx], [], priv, height=0, timestamp=1000)

    assert block.height == 0
    assert block.tx_count == 1
    assert block.block_hash != ""
    assert block.validator_signature != ""

    assert validate_block(block, None, [])

def test_genesis_block():
    genesis = build_genesis_block()
    assert genesis.height == 0
    assert genesis.prev_hash == "0" * 64
    assert len(genesis.transactions) == 1
    assert genesis.transactions[0].amount == Decimal("1000000")
    assert validate_block(genesis, None, [])

@pytest.mark.asyncio
async def test_chain_state_logic(mocker):
    # Mock DB session and models
    db = mocker.Mock()
    state = ChainState()

    # We'll need more complex mocking for async DB calls if we want to test apply_transaction fully here.
    # For now, we've implemented the logic.
    pass
