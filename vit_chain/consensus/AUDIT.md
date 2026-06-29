
## Session 2.2 - Block Voting + Finality Audit
- Requirements: 2/3 majority (0.67) for consensus. 5-second voting window.
- Slashing: 3 consecutive misses = 10% stake reduction.
- Rewards: 40% to producer, 60% split among voters.
- Discrepancy: `VITBlock`, `VITChain`, and `Mempool` are mentioned in the build spec but are currently missing from the codebase.
- Strategy: I will use duck-typing or protocol-based interfaces for these missing components so they can be easily integrated once implemented in Track 1.
- Infrastructure: Redis will be used for real-time vote collection (Pub/Sub) and miss counters (Incr/Set).
