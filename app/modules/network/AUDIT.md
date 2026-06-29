# Audit: Node Ecosystem (Track 9.1)

## What Exists
- `app/modules/network/models.py`: Contains `NodeActivity` and `NetworkSnapshot` models. `NodeActivity` has a `node_type` field but no validation against a registry.
- `app/modules/network/routes.py`: Contains API endpoints for network stats, node listing, and activity recording. Has a `/join` endpoint that hardcodes `node_type="storage"`.

## What's Missing
- `app/modules/network/node_types.py`: The registry defining different node types (storage, validator, campus, android, gpu) and their requirements/multipliers is missing.
- `app/modules/network/capabilities.py`: The client-side component for reporting node capabilities is missing.
- `app/modules/network/rewards_matrix.py`: The logic for calculating epoch rewards based on node type and performance is missing.
- `/api/network/nodes/{node_id}/capabilities` endpoint: Mentioned in the build spec for `capabilities.py` but not present in `routes.py`. (Note: I am restricted from modifying `routes.py`).

## What's Broken / Improvements Needed
- The `node_type` in `routes.py` and `models.py` is currently a plain string without centralized validation or metadata.
- Reward calculations are currently not implemented in the existing codebase; they seem to be handled by the upcoming `RewardsMatrix`.
- `NodeActivity` in `models.py` uses `node_type` of length 20, but some display names or future types might exceed this if not careful (though current types fit).
