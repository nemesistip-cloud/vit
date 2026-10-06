from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from .core.block import VITBlock, build_block
from .core.transaction import VITTransaction, keccak256_hex
from .core.chain import VITChain
from .crypto.address import clean_hex_key, public_key_to_address, ZERO_ADDRESS
from app.config import get_env
import hashlib
import os
import time

GENESIS_TIMESTAMP = 1735689600  # 2025-01-01 00:00:00 UTC
INITIAL_SUPPLY = Decimal("1000000")
GENESIS_VALIDATOR = get_env("GENESIS_VALIDATOR_ADDRESS", "VIT_GENESIS_VALIDATOR_ADDRESS")

def _resolve_treasury_key() -> str:
    raw = get_env("VIT_TREASURY_PRIVATE_KEY", "")
    cleaned = clean_hex_key(raw)
    if cleaned and len(cleaned) == 64:
        try:
            from coincurve import PrivateKey
            PrivateKey.from_hex(cleaned)
            return cleaned
        except Exception:
            pass
    return hashlib.sha256(b"vit-genesis-treasury-fallback-key").hexdigest()

_raw_treasury_key = get_env("VIT_TREASURY_PRIVATE_KEY", "")
TREASURY_PRIV_KEY = _resolve_treasury_key()

def build_genesis_block() -> VITBlock:
    """
    Creates block at height=0 with:
    - prev_hash = "0" * 64
    - Single genesis transaction: mint 1M VIT to treasury address
    - No storage proofs
    - validator_id = GENESIS_VALIDATOR
    """
    from coincurve import PrivateKey

    treasury_key = _resolve_treasury_key()
    priv = PrivateKey.from_hex(treasury_key)
    treasury_address = public_key_to_address(priv.public_key.format(compressed=False).hex())

    tx = VITTransaction(
        from_address=ZERO_ADDRESS,
        to_address=treasury_address,
        amount=INITIAL_SUPPLY,
        nonce=0,
        timestamp=GENESIS_TIMESTAMP,
        gas_fee=Decimal("0"),
        data={"type": "genesis_mint"}
    )

    tx.tx_hash = tx.compute_hash()

    raw_val_key = get_env("GENESIS_VALIDATOR_KEY", treasury_key)
    genesis_val_key = clean_hex_key(raw_val_key)
    if not genesis_val_key or len(genesis_val_key) != 64:
        genesis_val_key = treasury_key

    block = build_block(
        prev_block=None,
        transactions=[tx],
        storage_proofs=[],
        validator_key=genesis_val_key,
        height=0,
        timestamp=GENESIS_TIMESTAMP
    )

    return block

async def ensure_genesis(db: AsyncSession):
    """
    Idempotent: if block at height 0 exists, return it
    Otherwise build and persist genesis block
    """
    chain = VITChain()
    latest = await chain.get_latest_block(db)
    if latest and latest.height >= 0:
        return latest

    genesis_block = build_genesis_block()
    success = await chain.add_block(db, genesis_block)
    if not success:
        raise RuntimeError("Failed to add genesis block to VIT Chain")
    return genesis_block
