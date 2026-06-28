# AUDIT - vit_chain/p2p

## Status
Initial audit for `vit_chain/p2p` package. This is a new package part of Track 3 — P2P Network Layer.

## What Exists
- `vit_chain/p2p/` directory created.
- `vit_chain/p2p/__init__.py` (empty).

## What's Missing
- `vit_chain/p2p/models.py`: PeerNode SQLAlchemy model.
- `vit_chain/p2p/registry.py`: PeerRegistry for peer management.
- `vit_chain/p2p/discovery.py`: PeerDiscovery for Redis-based discovery.
- `vit_chain/p2p/bootstrap.py`: BootstrapManager for initial peer acquisition.
- `vit_chain/tests/test_p2p.py`: Test suite for P2P layer.

## What's Broken
- N/A (New implementation).

## Implementation Plan (Session 3.1)
1. Define `PeerNode` model in `models.py`.
2. Implement `PeerRegistry` in `registry.py` with scoring logic.
3. Implement `PeerDiscovery` in `discovery.py` with Redis HSET and Pub/Sub.
4. Implement `BootstrapManager` in `bootstrap.py` for initial bootstrapping.
5. Verify with comprehensive tests in `test_p2p.py`.

## Implementation Plan (Session 3.2)
1. Implement `protocol.py` for P2P message types and serialization.
2. Implement `connection.py` for managing WebSocket peer connections.
3. Implement `gossip.py` for message propagation and handling.
4. Implement `sync.py` for chain state synchronization.
5. Verify with `test_p2p_gossip.py`.
