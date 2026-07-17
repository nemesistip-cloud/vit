from .hash import keccak256_hex

VIT_ADDRESS_PREFIX = "VIT"
ZERO_ADDRESS = VIT_ADDRESS_PREFIX + "0" * 40

def public_key_to_address(public_key_hex: str) -> str:
    """
    1. Keccak-256 hash of public key bytes (skip leading 0x04 if present)
    2. Take last 20 bytes
    3. Encode as hex
    4. Prefix with "VIT" → e.g. "VIT3a4b5c6d..."
    """
    pub_bytes = bytes.fromhex(public_key_hex)
    if pub_bytes[0] == 0x04:
        pub_bytes = pub_bytes[1:]

    # keccak256_hex returns a hex string
    k_hash = keccak256_hex(pub_bytes)
    # last 20 bytes = last 40 hex chars
    address_part = k_hash[-40:]
    return f"{VIT_ADDRESS_PREFIX}{address_part}"

def validate_address(address: str) -> bool:
    """Returns True if address starts with 'VIT' and has correct length."""
    if not address.startswith(VIT_ADDRESS_PREFIX):
        return False
    # Prefix (3) + Hex (40) = 43 chars
    if len(address) != 43:
        return False
    # Check if the rest is valid hex
    try:
        int(address[3:], 16)
        return True
    except ValueError:
        return False
