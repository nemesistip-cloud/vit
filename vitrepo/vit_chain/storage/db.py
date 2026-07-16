from sqlalchemy import Column, Integer, String, Numeric, DateTime, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from app.db.database import Base
from decimal import Decimal

class ChainBlock(Base):
    __tablename__ = "chain_blocks"
    height = Column(Integer, primary_key=True)
    block_hash = Column(String(64), unique=True, index=True, nullable=False)
    prev_hash = Column(String(64), index=True)
    merkle_root = Column(String(64))
    state_root = Column(String(64))
    timestamp = Column(Integer, index=True)
    validator_id = Column(String(64), index=True)
    validator_signature = Column(String(256))
    tx_count = Column(Integer)
    total_fees = Column(Numeric(36, 18))
    block_reward = Column(Numeric(36, 18))
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChainTransaction(Base):
    __tablename__ = "chain_transactions"
    tx_hash = Column(String(64), primary_key=True)
    block_height = Column(Integer, ForeignKey("chain_blocks.height"), nullable=True, index=True)
    from_address = Column(String(64), index=True)
    to_address = Column(String(64), index=True)
    amount = Column(Numeric(36, 18))
    nonce = Column(Integer)
    gas_fee = Column(Numeric(36, 18))
    tx_type = Column(String(20)) # transfer|stake|reward|storage
    data = Column(JSON)
    signature = Column(String(256))
    timestamp = Column(Integer, index=True)
    status = Column(String(20), index=True)

class ChainAccount(Base):
    __tablename__ = "chain_accounts"
    address = Column(String(64), primary_key=True)
    balance = Column(Numeric(36, 18), default=Decimal("0"))
    staked = Column(Numeric(36, 18), default=Decimal("0"))
    nonce = Column(Integer, default=0)
    first_seen_height = Column(Integer)
    last_active_height = Column(Integer)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

async def ensure_chain_tables(engine):
    """
    Create all tables.
    Operator should call this from bootstrap.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
