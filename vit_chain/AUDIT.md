# AUDIT - vit_chain

## Status
Initial audit for `vit_chain` package. This is a new package part of Track 1 — VIT Chain Core.

## What Exists
- `vit_chain/` directory structure.
- `requirements.txt` updated with `eth-hash[pycryptodome]` and `coincurve`.

## What's Missing
- `vit_chain/crypto/hash.py`: Cryptographic hashing functions.
- `vit_chain/crypto/merkle.py`: Merkle Tree implementation.
- `vit_chain/crypto/ecdsa.py`: ECDSA keypair generation and signing.
- `vit_chain/crypto/address.py`: VIT address derivation.
- `vit_chain/tests/test_crypto.py`: Test suite for the above.

## What's Broken
- N/A (New implementation).

## Implementation Plan
1. Implement `hash.py` using `hashlib` and `eth-hash`.
2. Implement `merkle.py` for block and transaction hashing.
3. Implement `ecdsa.py` using `coincurve`.
4. Implement `address.py` following the specified derivation path.
5. Verify everything with `test_crypto.py`.
