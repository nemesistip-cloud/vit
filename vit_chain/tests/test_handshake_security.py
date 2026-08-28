import time

from vit_chain.crypto.ecdsa import generate_keypair, sign_transaction
from vit_chain.crypto.hash import sha256_bytes
from vit_chain.p2p.protocol import handshake_signing_bytes, verify_handshake


def make_handshake(private_key, public_key, **overrides):
    message = {
        "node_id": "NODE_1",
        "public_key": public_key,
        "chain_height": 3,
        "node_type": "validator",
        "capabilities": {},
        "protocol_version": "1.0",
        "timestamp": time.time(),
        "nonce": "a" * 32,
    }
    message.update(overrides)
    message["signature"] = sign_transaction(
        private_key,
        sha256_bytes(handshake_signing_bytes(message)),
    )
    return message


def test_valid_handshake_is_accepted_once():
    private_key, public_key = generate_keypair()
    message = make_handshake(private_key, public_key)
    seen = set()

    assert verify_handshake(message, seen)
    assert not verify_handshake(message, seen)


def test_invalid_signature_is_rejected():
    private_key, public_key = generate_keypair()
    message = make_handshake(private_key, public_key)
    message["signature"] = "00"

    assert not verify_handshake(message, set())


def test_wrong_public_key_is_rejected():
    private_key, public_key = generate_keypair()
    _, wrong_public_key = generate_keypair()
    message = make_handshake(private_key, public_key)
    message["public_key"] = wrong_public_key

    assert not verify_handshake(message, set())


def test_stale_handshake_is_rejected():
    private_key, public_key = generate_keypair()
    message = make_handshake(private_key, public_key, timestamp=0)

    assert not verify_handshake(message, set(), now=100)


def test_malformed_handshake_is_rejected():
    assert not verify_handshake({"type": "handshake"}, set())