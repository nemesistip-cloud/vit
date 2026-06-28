# AUDIT - vit_chain/consensus

## Status
Final audit for Track 2 — Proof of Storage Consensus (Integration phase).

## Existing State
- Session 2.1 & 2.2 implemented: Challenges, Voting, Finalizer, Slashing.
- Comprehensive tests in `test_consensus.py` and `test_consensus_v2.py`.

## Discrepancies & Challenges
- Build Spec for 2.3 refers to `vit_chain.core.block.build_block`, `VITBlock`, `VITChain`, and `Mempool`.
- These components are expected from Track 1 but are currently missing in the visible codebase.
- `app/modules/network/models.py` doesn't explicitly store "node type" for reward tiers, but `NodeActivity` has a `node_type` field. `UserStorageNode` has a `status` field.
- I will implement robust placeholders/interfaces for the missing core chain components to allow full consensus orchestration, while ensuring the integration is logically sound.

## Implementation Plan
1. Implement `BlockProducer` in `producer.py` with mock/stub integration for Mempool and VITChain.
2. Implement `StorageRewardCalculator` in `rewards.py` with tier-based logic.
3. Implement `ConsensusEngine` in `engine.py` to tie all phases together in the master loop.
4. Add comprehensive end-to-end integration tests in `test_consensus_full.py`.
