import pytest
from decimal import Decimal
from vit_chain.core.block import VITBlock, build_block, validate_block
from vit_chain.core.transaction import VITTransaction, create_transaction, Mempool
from vit_chain.core.manager import BlockchainManager
from vit_chain.crypto.ecdsa import generate_keypair
from vit_chain.crypto.address import public_key_to_address
import time

@pytest.fixture
def manager():
    return BlockchainManager(mempool_size=10, tx_ttl=10)

@pytest.fixture
def keys():
    priv, pub = generate_keypair()
    return priv, pub

def test_mempool_ttl_and_size(keys):
    mempool = Mempool(max_size=2, tx_ttl=1)
    priv, pub = keys
    to_addr = "VIT" + "1" * 40

    # 1. Test TTL
    tx1 = create_transaction(priv, to_addr, Decimal("1"), 0, timestamp=int(time.time()) - 2)
    assert not mempool.add(tx1) # Expired

    # 2. Test Max Size
    tx2 = create_transaction(priv, to_addr, Decimal("1"), 1)
    tx3 = create_transaction(priv, to_addr, Decimal("1"), 2)
    tx4 = create_transaction(priv, to_addr, Decimal("1"), 3)

    assert mempool.add(tx2)
    assert mempool.add(tx3)
    assert not mempool.add(tx4) # Full
    assert mempool.size() == 2

def test_block_with_version_and_nonce(keys):
    priv, pub = keys
    tx = create_transaction(priv, "VIT" + "1" * 40, Decimal("10"), 0)

    block = build_block(None, [tx], [], priv, height=0, timestamp=1000, version=2, nonce=12345)

    assert block.version == 2
    assert block.nonce == 12345
    assert block.block_hash == block.compute_hash()
    assert validate_block(block, None, [])

@pytest.mark.asyncio
async def test_manager_transaction_events(mocker, manager, keys):
    mock_publish = mocker.patch("app.core.event_bus.event_bus.publish")
    priv, pub = keys
    tx = create_transaction(priv, "VIT" + "2" * 40, Decimal("5"), 0)

    success = await manager.add_transaction(tx)
    assert success
    mock_publish.assert_called_with("TransactionAccepted", tx.to_dict(), sender="blockchain_manager")

@pytest.mark.asyncio
async def test_manager_block_processing(mocker, manager, keys):
    # Mock dependencies
    db = mocker.Mock()
    mocker.patch.object(manager.chain, "get_latest_block", return_value=None)
    mocker.patch.object(manager.chain, "add_block", return_value=True)
    mocker.patch.object(manager.state, "get_state_root", return_value="root")
    mocker.patch.object(manager.indexer, "index_block", return_value=None)
    mock_publish = mocker.patch("app.core.event_bus.event_bus.publish")

    priv, pub = keys
    tx = create_transaction(priv, "VIT" + "2" * 40, Decimal("5"), 0)
    manager.mempool.add(tx)

    block = build_block(None, [tx], [], priv, height=0)

    success = await manager.process_new_block(db, block)
    assert success
    assert manager.mempool.size() == 0
    mock_publish.assert_any_call("BlockAdded", mocker.ANY, sender="blockchain_manager")

@pytest.mark.asyncio
async def test_ledger_integrity_verification(mocker, manager, keys):
    db = mocker.Mock()
    priv, pub = keys

    # Create a small chain
    b0 = build_block(None, [], [], priv, height=0, timestamp=100)
    b1 = build_block(b0, [], [], priv, height=1, timestamp=115)

    mocker.patch.object(manager.chain, "chain_height", return_value=1)

    def get_block(db, h):
        return b0 if h == 0 else b1

    mocker.patch.object(manager.chain, "get_block_by_height", side_effect=get_block)

    is_valid = await manager.verify_chain_integrity(db)
    assert is_valid

    # Corrupt a block
    b1.prev_hash = "wrong"
    is_valid = await manager.verify_chain_integrity(db)
    assert not is_valid
