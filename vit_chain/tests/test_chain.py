import pytest
from decimal import Decimal
from unittest.mock import AsyncMock
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
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

@pytest.mark.asyncio
async def test_transaction_creation_and_verification(keys):
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

@pytest.mark.asyncio
async def test_mempool():
    mempool = Mempool()
    priv, pub = generate_keypair()
    to_addr = "VIT" + "1" * 40
    tx = create_transaction(priv, to_addr, Decimal("10"), 0)

    assert mempool.add(tx)
    assert mempool.size() == 1
    assert not mempool.add(tx) # Duplicate

    pending = mempool.get_pending()
    assert len(pending) == 1
    assert pending[0].tx_hash == tx.tx_hash

    mempool.remove([tx.tx_hash])
    assert mempool.size() == 0

@pytest.mark.asyncio
async def test_block_building_and_validation(keys):
    priv, pub = keys
    to_addr = "VIT" + "1" * 40
    tx = create_transaction(priv, to_addr, Decimal("10"), 0)

    block = build_block(None, [tx], [], priv, height=0, timestamp=1000)

    assert block.height == 0
    assert block.tx_count == 1
    assert block.block_hash != ""
    assert block.validator_signature != ""
    assert len(block.state_commitment) == 64

    assert validate_block(block, None, [])

@pytest.mark.asyncio
async def test_state_commitment_changes_across_blocks(keys):
    priv, _ = keys
    to_addr = "VIT" + "2" * 40
    tx = create_transaction(priv, to_addr, Decimal("10"), 0)
    first = build_block(None, [tx], [], priv, height=0, timestamp=1000)
    second = build_block(first, [], [], priv, height=1, timestamp=1015)

    assert first.state_commitment != second.state_commitment
    assert validate_block(second, first, [])

    second.state_commitment = "0" * 64
    assert not validate_block(second, first, [])

@pytest.mark.asyncio
async def test_genesis_block():
    genesis = build_genesis_block()
    assert genesis.height == 0
    assert genesis.prev_hash == "0" * 64
    assert len(genesis.transactions) == 1
    assert genesis.transactions[0].amount == Decimal("1000000")
    assert validate_block(genesis, None, [])


@pytest.mark.asyncio
async def test_rejected_block_rolls_back_prior_transaction_mutations(monkeypatch):
    from vit_chain.core.chain import VITChain
    from vit_chain.core.block import VITBlock

    class State:
        def __init__(self):
            self.applied = 0

        async def apply_transaction(self, db, _tx):
            await db.execute(text("UPDATE test_balances SET balance = balance + 1 WHERE id = 1"))
            self.applied += 1
            return self.applied == 1

        async def apply_block_reward(self, *_args):
            raise AssertionError("rejected block must not apply rewards")

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE test_balances (id INTEGER PRIMARY KEY, balance INTEGER NOT NULL)"))
        await connection.execute(text("INSERT INTO test_balances (id, balance) VALUES (1, 0)"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as db:
            chain = VITChain()
            chain.state = State()

            async def no_prior_block(_db):
                return None

            chain.get_latest_block = no_prior_block
            monkeypatch.setattr("vit_chain.core.chain.validate_block", lambda *_args, **_kwargs: True)
            block = VITBlock(
                height=0,
                prev_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=1,
                validator_id="VIT" + "1" * 40,
                transactions=[object(), object()],
                tx_count=2,
                total_fees=Decimal("0"),
                block_reward=Decimal("10"),
            )

            accepted = await chain.add_block(db, block)
            assert accepted is False
            assert chain.state.applied == 2
            await db.commit()

            balance = await db.scalar(text("SELECT balance FROM test_balances WHERE id = 1"))
            assert balance == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_indexer_failure_rolls_back_block_and_returns_rejected(monkeypatch):
    from vit_chain.core.chain import VITChain
    from vit_chain.core.block import VITBlock

    class State:
        async def apply_transaction(self, *_args):
            return True

        async def apply_block_reward(self, db, *_args):
            await db.execute(text("UPDATE test_balances SET balance = balance + 1 WHERE id = 1"))

    async def fail_indexing(*_args):
        raise RuntimeError("index write failed")

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE test_balances (id INTEGER PRIMARY KEY, balance INTEGER NOT NULL)"))
        await connection.execute(text("INSERT INTO test_balances (id, balance) VALUES (1, 0)"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as db:
            chain = VITChain()
            chain.state = State()
            chain.get_latest_block = AsyncMock(return_value=None)
            monkeypatch.setattr("vit_chain.core.chain.validate_block", lambda *_args, **_kwargs: True)
            monkeypatch.setattr("vit_chain.storage.indexer.ChainIndexer.index_block", fail_indexing)
            block = VITBlock(
                height=0,
                prev_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=1,
                validator_id="VIT" + "1" * 40,
                transactions=[],
                tx_count=0,
                total_fees=Decimal("0"),
                block_reward=Decimal("1"),
            )

            assert await chain.add_block(db, block) is False
            await db.commit()
            balance = await db.scalar(text("SELECT balance FROM test_balances WHERE id = 1"))
            assert balance == 0
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_chain_state_logic(mocker):
    # Mock DB session and models
    db = mocker.Mock()
    state = ChainState()
    pass
