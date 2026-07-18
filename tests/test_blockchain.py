"""
Unit tests for vit_chain blockchain primitives.

These are pure unit tests — no DB, no ASGI app — so they run fast and
without infrastructure dependencies.
"""
import time
from decimal import Decimal

import pytest

from vit_chain.core.transaction import (
    VITTransaction,
    create_transaction,
    verify_transaction,
    Mempool,
)
from vit_chain.core.block import VITBlock, build_block, validate_block
from vit_chain.crypto.address import public_key_to_address


# ---------------------------------------------------------------------------
# Key fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def validator_key():
    """A deterministic private key for tests (NOT for production)."""
    return "92238e8a9a98ec05691c77ba77324ddbe94fe33588d5f27af2ac254f70810955"


@pytest.fixture
def recipient_address(validator_key):
    from coincurve import PrivateKey
    priv = PrivateKey.from_hex(validator_key)
    pub = priv.public_key.format(compressed=False).hex()
    return public_key_to_address(pub)


# ---------------------------------------------------------------------------
# VITTransaction
# ---------------------------------------------------------------------------

class TestVITTransaction:

    def test_create_and_verify_transaction(self, validator_key, recipient_address):
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("100"),
            nonce=1,
        )
        assert tx.from_address != ""
        assert tx.tx_hash != ""
        assert tx.signature != ""
        assert verify_transaction(tx), "Transaction should verify with valid ECDSA signature"

    def test_tampered_amount_fails_verification(self, validator_key, recipient_address):
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("100"),
            nonce=2,
        )
        # Tamper with the amount after signing — tx_hash is now stale
        tx.amount = Decimal("999999")
        # verify_transaction recomputes the hash and detects the mismatch
        assert not verify_transaction(tx), "Tampered tx should NOT verify (hash mismatch)"

    def test_negative_amount_fails_verification(self, validator_key, recipient_address):
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("50"),
            nonce=3,
        )
        tx.amount = Decimal("-1")
        assert not verify_transaction(tx)

    def test_compute_hash_is_deterministic(self, validator_key, recipient_address):
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("10"),
            nonce=4,
        )
        h1 = tx.compute_hash()
        h2 = tx.compute_hash()
        assert h1 == h2

    def test_serialise_roundtrip(self, validator_key, recipient_address):
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("42"),
            nonce=5,
        )
        d = tx.to_dict()
        assert d["amount"] == "42"
        assert d["gas_fee"] == str(tx.gas_fee)
        assert "signature" in d
        assert "tx_hash" in d


# ---------------------------------------------------------------------------
# Mempool
# ---------------------------------------------------------------------------

class TestMempool:

    def test_add_transaction(self, validator_key, recipient_address):
        mp = Mempool()
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("1"),
            nonce=10,
        )
        assert mp.add_transaction(tx)

    def test_duplicate_rejected(self, validator_key, recipient_address):
        mp = Mempool()
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("1"),
            nonce=11,
        )
        assert mp.add_transaction(tx)
        assert not mp.add_transaction(tx), "Duplicate should be rejected"


# ---------------------------------------------------------------------------
# Block building + validation
# ---------------------------------------------------------------------------

class TestVITBlock:

    def _genesis(self, validator_key, recipient_address):
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("1000000"),
            nonce=0,
        )
        return build_block(
            prev_block=None,
            transactions=[tx],
            storage_proofs=[],
            validator_key=validator_key,
            height=0,
            timestamp=1735689600,
        )

    def test_genesis_block_validates(self, validator_key, recipient_address):
        genesis = self._genesis(validator_key, recipient_address)
        assert validate_block(genesis, prev_block=None), "Genesis block should be valid"

    def test_child_block_validates(self, validator_key, recipient_address):
        genesis = self._genesis(validator_key, recipient_address)
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("10"),
            nonce=1,
        )
        child = build_block(
            prev_block=genesis,
            transactions=[tx],
            storage_proofs=[],
            validator_key=validator_key,
            height=1,
            timestamp=genesis.timestamp + 15,
        )
        assert validate_block(child, prev_block=genesis)

    def test_wrong_prev_hash_fails(self, validator_key, recipient_address):
        genesis = self._genesis(validator_key, recipient_address)
        tx = create_transaction(
            from_key=validator_key,
            to_address=recipient_address,
            amount=Decimal("5"),
            nonce=1,
        )
        child = build_block(
            prev_block=genesis,
            transactions=[tx],
            storage_proofs=[],
            validator_key=validator_key,
            height=1,
            timestamp=genesis.timestamp + 15,
        )
        # Tamper with prev_hash
        child.prev_hash = "0" * 64
        assert not validate_block(child, prev_block=genesis)

    def test_hash_tamper_fails(self, validator_key, recipient_address):
        genesis = self._genesis(validator_key, recipient_address)
        genesis.block_hash = "0" * 64  # tamper
        assert not validate_block(genesis, prev_block=None)
