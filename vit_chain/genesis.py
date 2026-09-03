from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from .core.block import VITBlock, build_block
from .core.transaction import VITTransaction, keccak256_hex
from .core.chain import VITChain
from app.config import get_env
import time

GENESIS_TIMESTAMP = 1735689600  # 2025-01-01 00:00:00 UTC
INITIAL_SUPPLY = Decimal("1000000")
GENESIS_VALIDATOR = get_env("GENESIS_VALIDATOR_ADDRESS", "VIT_GENESIS_VALIDATOR_ADDRESS")
_raw_treasury_key = get_env("VIT_TREASURY_PRIVATE_KEY", "")
if not _raw_treasury_key:
    import logging as _log
    _log.getLogger(__name__).warning(
        "VIT_TREASURY_PRIVATE_KEY is not set — using the embedded dev key. "
        "THIS MUST NEVER HAPPEN IN PRODUCTION. Set the secret in Render."
    )
    _raw_treasury_key = "92238e8a9a98ec05691c77ba77324ddbe94fe33588d5f27af2ac254f70810955"
TREASURY_PRIV_KEY = _raw_treasury_key

def build_genesis_block() -> VITBlock:
    """
    Creates block at height=0 with:
    - prev_hash = "0" * 64
    - Single genesis transaction: mint 1M VIT to treasury address
    - No storage proofs
    - validator_id = GENESIS_VALIDATOR
    """
    from coincurve import PrivateKey
    from .crypto.address import public_key_to_address

    # Deriving treasury address
    priv = PrivateKey.from_hex(TREASURY_PRIV_KEY)
    treasury_address = public_key_to_address(priv.public_key.format(compressed=False).hex())

    # Genesis transaction (no from_address, or special zero address)
    from .crypto.address import ZERO_ADDRESS

    # We create a special transaction for genesis
    tx = VITTransaction(
        from_address=ZERO_ADDRESS,
        to_address=treasury_address,
        amount=INITIAL_SUPPLY,
        nonce=0,
        timestamp=GENESIS_TIMESTAMP,
        gas_fee=Decimal("0"),
        data={"type": "genesis_mint"}
    )

    # Genesis doesn't necessarily need a signature from ZERO_ADDRESS,
    # but we compute its hash.
    tx.tx_hash = tx.compute_hash()

    # Build block 0
    # For genesis, we might need a special build_block that doesn't sign or
    # uses a hardcoded signature.
    # But BUILD SPEC says: "validator_id = GENESIS_VALIDATOR"
    # We'll use a placeholder key for the genesis validator if not provided.
    genesis_val_key = get_env("GENESIS_VALIDATOR_KEY", TREASURY_PRIV_KEY)

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
