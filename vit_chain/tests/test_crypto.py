import pytest
from vit_chain.crypto.hash import (
    sha256_hex, sha256_bytes, keccak256_hex, double_sha256, hash_block_header
)
from vit_chain.crypto.merkle import MerkleTree, build_transaction_merkle
from vit_chain.crypto.ecdsa import (
    generate_keypair, sign_transaction, verify_signature, recover_public_key
)
from vit_chain.crypto.address import (
    public_key_to_address, validate_address, ZERO_ADDRESS, VIT_ADDRESS_PREFIX
)
from coincurve import PrivateKey

def test_hashing():
    data = b"vit_network"
    assert sha256_hex(data) == "532f9c0ec11477147ee79a686b08cbf02e826acab6c5b824392e2c7d122090dd"
    assert len(sha256_bytes(data)) == 32
    assert keccak256_hex(data) == "5fcb760ac2e68b37118274967406d207f290440aa0be6584ca67ab1c3426b90c"
    assert len(double_sha256(data)) == 32

def test_hash_block_header():
    h = hash_block_header("prev", "root", 12345, 1, "val1")
    assert isinstance(h, str)
    assert len(h) == 64
    # Deterministic check
    h2 = hash_block_header("prev", "root", 12345, 1, "val1")
    assert h == h2

def test_merkle_tree():
    leaves = [b"a", b"b", b"c", b"d"]
    tree = MerkleTree(leaves)
    assert len(tree.tree[0]) == 4
    assert len(tree.tree) == 3 # 4 -> 2 -> 1

    proof = tree.get_proof(0)
    assert MerkleTree.verify_proof(b"a", proof, tree.root)

    # Test padding
    leaves3 = [b"a", b"b", b"c"]
    tree3 = MerkleTree(leaves3)
    assert len(tree3.tree[0]) == 4
    assert tree3.leaves[3] == b""

def test_build_transaction_merkle():
    txs = [sha256_hex(b"tx1"), sha256_hex(b"tx2")]
    root = build_transaction_merkle(txs)
    assert isinstance(root, str)
    assert len(root) == 64

def test_ecdsa_roundtrip():
    priv_hex, pub_hex = generate_keypair()
    tx_hash = sha256_bytes(b"tx_data")

    sig_hex = sign_transaction(priv_hex, tx_hash)
    assert verify_signature(pub_hex, tx_hash, sig_hex)

    # Invalid signature
    assert not verify_signature(pub_hex, tx_hash, "00" * 70)

def test_ecdsa_recovery():
    priv = PrivateKey()
    priv_hex = priv.to_hex()
    pub_hex = priv.public_key.format(compressed=False).hex()
    tx_hash = sha256_bytes(b"tx_data")

    # Use recoverable signature for recovery test
    sig_rec_bytes = priv.sign_recoverable(tx_hash)
    sig_rec_hex = sig_rec_bytes.hex()

    recovered_pub = recover_public_key(tx_hash, sig_rec_hex)
    assert recovered_pub == pub_hex

def test_address_derivation():
    # Known keypair/address if possible, or just consistency
    priv_hex, pub_hex = generate_keypair()
    addr = public_key_to_address(pub_hex)

    assert addr.startswith(VIT_ADDRESS_PREFIX)
    assert validate_address(addr)
    assert len(addr) == 43

    # Determinism
    addr2 = public_key_to_address(pub_hex)
    assert addr == addr2

def test_zero_address():
    assert validate_address(ZERO_ADDRESS)
    assert ZERO_ADDRESS == "VIT0000000000000000000000000000000000000000"

def test_invalid_address():
    assert not validate_address("VIT123") # Too short
    assert not validate_address("BTC3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2") # Wrong prefix
    assert not validate_address("VIT" + "g" * 40) # Invalid hex
