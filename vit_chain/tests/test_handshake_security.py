import time

import pytest

from vit_node.keystore import Keystore
from vit_chain.p2p.protocol import handshake_signing_bytes, verify_handshake


@pytest.fixture
def identity(tmp_path):
    keystore = Keystore(tmp_path / "keystore.json")
    password = "test-password"
    keystore.create(password)
    return keystore, password


def make_handshake(keystore, password, **overrides):
    message = {
        "node_id": "NODE_1",
        "public_key": keystore.get_public_key(password),
        "chain_height": 3,
        "node_type": "validator",
        "capabilities": {},
        "protocol_version": "1.0",
        "timestamp": time.time(),
        "nonce": "a" * 32,
    }
    message.update(overrides)
    message["signature"] = keystore.sign(handshake_signing_bytes(message), password)
    return message


def test_valid_handshake_is_accepted_once(identity):
    keystore, password = identity
    message = make_handshake(keystore, password)
    seen = set()

    assert verify_handshake(message, seen)
    assert not verify_handshake(message, seen)


def test_tampered_handshake_is_rejected(identity):
    keystore, password = identity
    message = make_handshake(keystore, password)
    message["chain_height"] = 4

    assert not verify_handshake(message, set())


def test_invalid_signature_is_rejected(identity):
    keystore, password = identity
    message = make_handshake(keystore, password)
    message["signature"] = "00"

    assert not verify_handshake(message, set())


def test_wrong_public_key_is_rejected(identity, tmp_path):
    keystore, password = identity
    wrong_keystore = Keystore(tmp_path / "wrong-keystore.json")
    wrong_keystore.create("wrong-password")
    message = make_handshake(keystore, password)
    message["public_key"] = wrong_keystore.get_public_key("wrong-password")

    assert not verify_handshake(message, set())


def test_stale_handshake_is_rejected(identity):
    keystore, password = identity
    message = make_handshake(keystore, password, timestamp=0)

    assert not verify_handshake(message, set(), now=100)


def test_malformed_handshake_is_rejected():
    assert not verify_handshake({"type": "handshake"}, set())