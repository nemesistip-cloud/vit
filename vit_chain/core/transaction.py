import json
import time
from decimal import Decimal
from typing import Optional, Any
from dataclasses import dataclass, field, asdict
from ..crypto.hash import keccak256_hex
from ..crypto.ecdsa import sign_transaction, verify_signature, recover_public_key
from ..crypto.address import validate_address, public_key_to_address

@dataclass
class VITTransaction:
    from_address: str
    to_address: str
    amount: Decimal
    nonce: int
    timestamp: int
    gas_fee: Decimal = Decimal("0.001")
    data: Optional[dict] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    signature: str = ""
    status: str = "pending"
    tx_hash: str = ""

    def __post_init__(self):
        if not self.tx_hash:
            self.tx_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """keccak256 of canonical fields"""
        # Exclude signature, status, and tx_hash from the hash calculation
        payload = {
            "from_address": self.from_address,
            "to_address": self.to_address,
            "amount": str(self.amount),
            "nonce": self.nonce,
            "gas_fee": str(self.gas_fee),
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
        canonical_json = json.dumps(payload, sort_keys=True)
        return keccak256_hex(canonical_json.encode("utf-8"))

    def to_dict(self):
        d = asdict(self)
        d["amount"] = str(d["amount"])
        d["gas_fee"] = str(d["gas_fee"])
        return d

def create_transaction(from_key: str, to_address: str,
                       amount: Decimal, nonce: int,
                       data: dict = None, metadata: dict = None,
                       timestamp: int = None) -> VITTransaction:
    """Builds and signs transaction from private key"""
    if timestamp is None:
        timestamp = int(time.time())

    from coincurve import PrivateKey
    priv = PrivateKey.from_hex(from_key)
    pub_hex = priv.public_key.format(compressed=False).hex()
    from_address = public_key_to_address(pub_hex)

    tx = VITTransaction(
        from_address=from_address,
        to_address=to_address,
        amount=amount,
        nonce=nonce,
        timestamp=timestamp,
        data=data,
        metadata=metadata or {}
    )

    tx.signature = priv.sign_recoverable(bytes.fromhex(tx.tx_hash)).hex()
    return tx

def verify_transaction(tx: VITTransaction) -> bool:
    """Verifies: signature valid, amount >= 0, addresses valid"""
    if tx.amount < 0:
        return False
    if not validate_address(tx.from_address) or not validate_address(tx.to_address):
        return False

    recovered_pub = recover_public_key(bytes.fromhex(tx.tx_hash), tx.signature)
    if not recovered_pub:
        return False

    derived_address = public_key_to_address(recovered_pub)
    if derived_address != tx.from_address:
        return False

    return True

class Mempool:
    def __init__(self, max_size: int = 5000, tx_ttl: int = 3600):
        self._transactions: dict[str, VITTransaction] = {}
        self.max_size = max_size
        self.tx_ttl = tx_ttl

    def add(self, tx: VITTransaction) -> bool:
        """Rejects duplicates, invalid, and expired transactions"""
        if tx.tx_hash in self._transactions:
            return False
        if len(self._transactions) >= self.max_size:
            # Simple eviction: remove oldest if full, or just reject
            self.clear_expired()
            if len(self._transactions) >= self.max_size:
                return False
        if time.time() - tx.timestamp > self.tx_ttl:
            return False
        if not verify_transaction(tx):
            return False
        self._transactions[tx.tx_hash] = tx
        return True

    def clear_expired(self):
        """Removes transactions that have exceeded TTL"""
        now = time.time()
        expired = [h for h, tx in self._transactions.items() if now - tx.timestamp > self.tx_ttl]
        for h in expired:
            del self._transactions[h]

    def get_pending(self, limit: int = 500) -> list[VITTransaction]:
        """Returns highest-fee transactions first"""
        self.clear_expired()
        sorted_txs = sorted(
            self._transactions.values(),
            key=lambda tx: tx.gas_fee,
            reverse=True
        )
        return sorted_txs[:limit]

    def remove(self, tx_hashes: list[str]):
        """Called after block confirmation"""
        for tx_hash in tx_hashes:
            if tx_hash in self._transactions:
                del self._transactions[tx_hash]

    def size(self) -> int:
        return len(self._transactions)

    def contains(self, tx_hash: str) -> bool:
        return tx_hash in self._transactions
