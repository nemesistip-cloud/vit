import json
from decimal import Decimal
from typing import Optional
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
                       data: dict = None, timestamp: int = None) -> VITTransaction:
    """Builds and signs transaction from private key"""
    import time
    if timestamp is None:
        timestamp = int(time.time())

    # Deriving from_address from from_key to ensure consistency
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
        data=data
    )

    # Use recoverable signature for transactions
    tx.signature = priv.sign_recoverable(bytes.fromhex(tx.tx_hash)).hex()
    return tx

def verify_transaction(tx: VITTransaction) -> bool:
    """Verifies: signature valid, amount > 0, addresses valid"""
    if tx.amount <= 0:
        return False
    if not validate_address(tx.from_address) or not validate_address(tx.to_address):
        return False

    # Recover public key and check if it matches from_address
    # Since we use sign_recoverable, the signature is 65 bytes and can recover the public key.
    recovered_pub = recover_public_key(bytes.fromhex(tx.tx_hash), tx.signature)
    if not recovered_pub:
        return False

    derived_address = public_key_to_address(recovered_pub)
    if derived_address != tx.from_address:
        return False

    # For recoverable signatures, recovering the public key is sufficient verification
    # that the signature matches the message for *some* public key.
    # Matching it against from_address confirms it was signed by the owner.
    return True

class Mempool:
    def __init__(self):
        self._transactions: dict[str, VITTransaction] = {}

    def add(self, tx: VITTransaction) -> bool:
        """Rejects duplicates and invalid transactions"""
        if tx.tx_hash in self._transactions:
            return False
        if not verify_transaction(tx):
            return False
        self._transactions[tx.tx_hash] = tx
        return True

    def get_pending(self, limit: int = 500) -> list[VITTransaction]:
        """Returns highest-fee transactions first"""
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
