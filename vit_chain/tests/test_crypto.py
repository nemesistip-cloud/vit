import pytest
from vit_chain.crypto.hash import sha256_hex, hash_block_header, keccak256_hex
from vit_chain.crypto.merkle import MerkleTree, build_transaction_merkle
from vit_chain.crypto.ecdsa import generate_keypair, sign_transaction, verify_signature, recover_public_key
from vit_chain.crypto.address import public_key_to_address, validate_address, ZERO_ADDRESS

@pytest.mark.asyncio
async def test_hashing():
    data = b"vit_network"
    assert sha256_hex(data) == "532f9c0ec11477147ee79a686b08cbf02e826acab6c5b824392e2c7d122090dd"
    assert keccak256_hex(data) == "5fcb760ac2e68b37118274967406d207f290440aa0be6584ca67ab1c3426b90c"

@pytest.mark.asyncio
async def test_hash_block_header():
    h = hash_block_header("prev", "merkle", 123456789, 100, "val", version=1, nonce=0)
    assert len(h) == 64

@pytest.mark.asyncio
async def test_merkle_tree():
    leaves = [b"a", b"b", b"c"]
    tree = MerkleTree(leaves)
    assert tree.root != ""
    proof = tree.get_proof(0)
    assert MerkleTree.verify_proof(b"a", proof, tree.root)

@pytest.mark.asyncio
async def test_build_transaction_merkle():
    txs = ["aa" * 32, "bb" * 32]
    root = build_transaction_merkle(txs)
    assert len(root) == 64

@pytest.mark.asyncio
async def test_ecdsa_roundtrip():
    priv, pub = generate_keypair()
    msg = sha256_hex(b"hello").encode()
    sig = sign_transaction(priv, msg)
    assert verify_signature(pub, msg, sig)

@pytest.mark.asyncio
async def test_ecdsa_recovery():
    from coincurve import PrivateKey
    priv_key = PrivateKey()
    msg = sha256_hex(b"hello").encode()
    sig = priv_key.sign_recoverable(msg).hex()

    recovered = recover_public_key(msg, sig)
    assert recovered == priv_key.public_key.format(compressed=False).hex()

@pytest.mark.asyncio
async def test_address_derivation():
    priv, pub = generate_keypair()
    addr = public_key_to_address(pub)
    assert addr.startswith("VIT")
    assert len(addr) == 43
    assert validate_address(addr)

@pytest.mark.asyncio
async def test_zero_address():
    assert validate_address(ZERO_ADDRESS)
    assert ZERO_ADDRESS == "VIT" + "0" * 40

@pytest.mark.asyncio
async def test_invalid_address():
    assert not validate_address("0x123")
    assert not validate_address("VIT" + "1" * 39)
