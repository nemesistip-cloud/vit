from decimal import Decimal
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
from .transaction import VITTransaction
from ..crypto.hash import hash_block_header, sha256_hex
from ..crypto.merkle import MerkleTree
from ..crypto.ecdsa import recover_public_key
from ..crypto.address import public_key_to_address

BLOCK_TIME_SECONDS = 15
MAX_TXS_PER_BLOCK = 500
BASE_BLOCK_REWARD = Decimal("10")
CURRENT_BLOCK_VERSION = 1

@dataclass
class VITBlock:
    height: int
    prev_hash: str
    merkle_root: str
    timestamp: int
    validator_id: str
    transactions: list[VITTransaction]
    tx_count: int
    total_fees: Decimal
    block_reward: Decimal
    version: int = CURRENT_BLOCK_VERSION
    nonce: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    validator_signature: str = ""
    block_hash: str = ""
    storage_proofs: list[dict] = field(default_factory=list)
    consensus_votes: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.block_hash:
            self.block_hash = self.compute_hash()

    def to_dict(self) -> dict[str, Any]:
        return {
            "height": self.height,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "validator_id": self.validator_id,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "tx_count": self.tx_count,
            "total_fees": str(self.total_fees),
            "block_reward": str(self.block_reward),
            "version": self.version,
            "nonce": self.nonce,
            "metadata": self.metadata,
            "validator_signature": self.validator_signature,
            "block_hash": self.block_hash,
            "storage_proofs": self.storage_proofs,
            "consensus_votes": self.consensus_votes
        }

    def compute_hash(self) -> str:
        """Canonical block header hash — deterministic field ordering."""
        return hash_block_header(
            prev_hash=self.prev_hash,
            merkle_root=self.merkle_root,
            timestamp=self.timestamp,
            height=self.height,
            validator_id=self.validator_id,
            version=self.version,
            nonce=self.nonce
        )

def build_block(prev_block: Optional["VITBlock"],
                transactions: list[VITTransaction],
                storage_proofs: list[dict],
                validator_key: str,
                height: int = None,
                timestamp: int = None,
                version: int = CURRENT_BLOCK_VERSION,
                nonce: int = 0,
                metadata: dict = None) -> "VITBlock":
    """Assembles and signs a new block"""
    import time
    if timestamp is None:
        timestamp = int(time.time())

    if height is None:
        height = (prev_block.height + 1) if prev_block else 0

    prev_hash = prev_block.block_hash if prev_block else "0" * 64

    # Merkle root of transaction hashes
    tx_hashes = [bytes.fromhex(tx.tx_hash) for tx in transactions]
    merkle_tree = MerkleTree(tx_hashes)
    merkle_root = merkle_tree.root

    # Calculate total fees
    total_fees = sum(tx.gas_fee for tx in transactions)

    from coincurve import PrivateKey
    priv = PrivateKey.from_hex(validator_key)
    validator_id = public_key_to_address(priv.public_key.format(compressed=False).hex())

    block = VITBlock(
        height=height,
        prev_hash=prev_hash,
        merkle_root=merkle_root,
        timestamp=timestamp,
        validator_id=validator_id,
        transactions=transactions,
        tx_count=len(transactions),
        total_fees=total_fees,
        block_reward=BASE_BLOCK_REWARD,
        storage_proofs=storage_proofs,
        version=version,
        nonce=nonce,
        metadata=metadata or {}
    )

    # Sign the block hash (recoverable)
    block.validator_signature = priv.sign_recoverable(bytes.fromhex(block.block_hash)).hex()
    return block

def validate_block(block: VITBlock, prev_block: Optional[VITBlock],
                   known_validators: Optional[list[str]] = None,
                   consensus_validator: Optional[Callable] = None) -> bool:
    """
    Validates: hash correct, prev_hash matches, merkle_root valid,
               validator signature valid, timestamp reasonable
    """
    # 1. Check height
    if prev_block:
        if block.height != prev_block.height + 1:
            return False
        if block.prev_hash != prev_block.block_hash:
            return False
    else:
        if block.height != 0:
            return False
        if block.prev_hash != "0" * 64:
            return False

    # 2. Check hash
    if block.block_hash != block.compute_hash():
        return False

    # 3. Check Merkle root
    tx_hashes = [bytes.fromhex(tx.tx_hash) for tx in block.transactions]
    merkle_tree = MerkleTree(tx_hashes)
    if block.merkle_root != merkle_tree.root:
        return False

    # 4. Check validator
    if known_validators is not None:
        if block.validator_id not in known_validators:
            return False

    # 5. Check signature
    recovered_pub = recover_public_key(bytes.fromhex(block.block_hash), block.validator_signature)
    if not recovered_pub:
        return False

    if public_key_to_address(recovered_pub) != block.validator_id:
        return False

    # 6. Check timestamp (simple check)
    if prev_block and block.timestamp <= prev_block.timestamp:
        return False

    # 7. Consensus-specific validation (if provided)
    if consensus_validator:
        if not consensus_validator(block):
            return False

    return True
