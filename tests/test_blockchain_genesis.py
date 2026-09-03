import pytest
import time
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.database import Base
from vit_chain.genesis import ensure_genesis, build_genesis_block, INITIAL_SUPPLY
from vit_chain.core.chain import VITChain
from vit_chain.core.manager import BlockchainManager
from vit_chain.core.transaction import VITTransaction
from vit_chain.crypto.address import ZERO_ADDRESS

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def async_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_genesis_creation_and_idempotency(async_db):
    chain = VITChain()
    manager = BlockchainManager()

    # Initially empty
    latest = await chain.get_latest_block(async_db)
    assert latest is None

    # Ensure genesis
    genesis_block = await ensure_genesis(async_db)
    await async_db.commit()

    assert genesis_block is not None
    assert genesis_block.height == 0

    # Verify persisted in DB
    latest_after = await chain.get_latest_block(async_db)
    assert latest_after is not None
    assert latest_after.height == 0
    assert latest_after.block_hash == genesis_block.block_hash

    # Verify recipient received initial supply (plus block reward if same address)
    tx = genesis_block.transactions[0]
    treasury_address = tx.to_address
    balance = await chain.state.get_balance(async_db, treasury_address)
    assert balance >= INITIAL_SUPPLY

    # Idempotency check: repeat ensure_genesis
    second_genesis = await ensure_genesis(async_db)
    assert second_genesis.block_hash == genesis_block.block_hash

    # Verify chain integrity
    integrity_valid = await manager.verify_chain_integrity(async_db)
    assert integrity_valid is True

@pytest.mark.asyncio
async def test_zero_address_security(async_db):
    chain = VITChain()
    await ensure_genesis(async_db)
    await async_db.commit()

    # Invalid ZERO_ADDRESS tx without genesis_mint type
    fake_tx = VITTransaction(
        from_address=ZERO_ADDRESS,
        to_address="VIT0000000000000000000000000000000000000001",
        amount=Decimal("100"),
        nonce=0,
        timestamp=int(time.time()),
        data={"type": "user_transfer"}
    )

    res = await chain.state.apply_transaction(async_db, fake_tx)
    assert res is False

    # Invalid ZERO_ADDRESS tx with invalid nonce
    fake_tx2 = VITTransaction(
        from_address=ZERO_ADDRESS,
        to_address="VIT0000000000000000000000000000000000000001",
        amount=Decimal("100"),
        nonce=1,
        timestamp=int(time.time()),
        data={"type": "genesis_mint"}
    )

    res2 = await chain.state.apply_transaction(async_db, fake_tx2)
    assert res2 is False

@pytest.mark.asyncio
async def test_normal_transaction_requires_valid_wallet(async_db):
    chain = VITChain()
    await ensure_genesis(async_db)
    await async_db.commit()

    # Normal transaction from unknown address
    normal_tx = VITTransaction(
        from_address="VIT1111111111111111111111111111111111111111",
        to_address="VIT2222222222222222222222222222222222222222",
        amount=Decimal("50"),
        nonce=0,
        timestamp=int(time.time())
    )

    res = await chain.state.apply_transaction(async_db, normal_tx)
    assert res is False
