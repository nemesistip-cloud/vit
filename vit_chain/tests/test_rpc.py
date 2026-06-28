import pytest
from decimal import Decimal
from vit_chain.rpc.server import VITChainRPC
from vit_chain.core.block import build_block
from vit_chain.core.transaction import create_transaction
from vit_chain.storage.indexer import ChainIndexer
from vit_chain.storage.db import ChainBlock, ChainTransaction, ChainAccount
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base

@pytest.fixture(scope="module")
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine

@pytest.fixture
async def db(engine):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session

@pytest.mark.asyncio
async def test_rpc_handlers(db):
    rpc = VITChainRPC()

    # Test net_version
    req = {"jsonrpc": "2.0", "method": "net_version", "params": [], "id": 1}
    resp = await rpc.handle(req, db)
    assert resp["result"] == "7764"

    # Test eth_chainId
    req = {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 2}
    resp = await rpc.handle(req, db)
    assert resp["result"] == "0x1e54"

    # Test eth_blockNumber (empty)
    req = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 3}
    resp = await rpc.handle(req, db)
    assert resp["result"] == "0x0"

@pytest.mark.asyncio
async def test_indexing_and_rpc_balance(db):
    indexer = ChainIndexer()
    from vit_chain.crypto.ecdsa import generate_keypair
    priv, pub = generate_keypair()
    from vit_chain.crypto.address import public_key_to_address
    addr = public_key_to_address(pub)

    # Create a block with a transaction
    tx = create_transaction(priv, "VIT_TO_ADDR", Decimal("10"), 0)
    # Give sender some balance in ChainAccount first
    acc = ChainAccount(address=addr, balance=Decimal("100"), nonce=0, first_seen_height=0, last_active_height=0)
    db.add(acc)
    await db.commit()

    block = build_block(None, [tx], [], priv, height=0, timestamp=1000)
    await indexer.index_block(db, block)
    await db.commit()

    # Check balance via RPC
    rpc = VITChainRPC()
    req = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [addr, "latest"], "id": 1}
    resp = await rpc.handle(req, db)
    # 100 - (10 + 0.001) [tx] + (10 + 0.001) [reward] = 100
    assert int(resp["result"], 16) == 100 * 10**18

    # Check block number
    req = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 2}
    resp = await rpc.handle(req, db)
    assert resp["result"] == "0x0"
