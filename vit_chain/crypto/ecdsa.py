from coincurve import PrivateKey, PublicKey

def generate_keypair() -> tuple[str, str]:
    """Returns (private_key_hex, public_key_hex) — secp256k1 uncompressed."""
    priv = PrivateKey()
    pub = priv.public_key
    return priv.to_hex(), pub.format(compressed=False).hex()

def sign_transaction(private_key_hex: str, tx_hash: bytes) -> str:
    """Returns DER-encoded signature as hex string."""
    priv = PrivateKey.from_hex(private_key_hex)
    return priv.sign(tx_hash).hex()

def verify_signature(public_key_hex: str,
                   tx_hash: bytes,
                   signature_hex: str) -> bool:
    """Returns True if signature is valid. Supports both DER and recoverable formats."""
    try:
        pub = PublicKey(bytes.fromhex(public_key_hex))
        sig_bytes = bytes.fromhex(signature_hex)
        if len(sig_bytes) == 65:
            # Try as recoverable first
            try:
                recovered = PublicKey.from_signature_and_message(sig_bytes, tx_hash)
                return recovered.format(compressed=False).hex() == public_key_hex
            except Exception:
                return False
        return pub.verify(sig_bytes, tx_hash)
    except Exception:
        return False

def recover_public_key(tx_hash: bytes, signature_hex: str) -> str:
    """Recovers public key from 65-byte recoverable signature + hash."""
    try:
        sig_bytes = bytes.fromhex(signature_hex)
        pub = PublicKey.from_signature_and_message(sig_bytes, tx_hash)
        return pub.format(compressed=False).hex()
    except Exception:
        return ""
