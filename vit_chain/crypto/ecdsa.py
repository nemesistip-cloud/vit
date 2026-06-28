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
    """Returns True if signature is valid."""
    try:
        pub = PublicKey(bytes.fromhex(public_key_hex))
        return pub.verify(bytes.fromhex(signature_hex), tx_hash)
    except Exception:
        return False

def recover_public_key(tx_hash: bytes, signature_hex: str) -> str:
    """Recovers public key from signature + hash (for tx validation)."""
    # Note: Traditional DER signatures are not recoverable without the recovery ID (v).
    # However, coincurve's PublicKey.from_signature_and_message expects a 65-byte
    # recoverable signature [r (32) | s (32) | v (1)].
    # If the provided signature is 65 bytes, we treat it as recoverable.
    # If it is DER, recovery is not possible with this function.
    try:
        sig_bytes = bytes.fromhex(signature_hex)
        pub = PublicKey.from_signature_and_message(sig_bytes, tx_hash)
        return pub.format(compressed=False).hex()
    except Exception:
        return ""
