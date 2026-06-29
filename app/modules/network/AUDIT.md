# Audit: Node Ecosystem (Track 9.2)

## What Exists
- `app/modules/network/node_types.py`: Implemented in Session 9.1, defines the "campus" node type with a multiplier of 3.0.
- `app/modules/network/models.py`: Contains `NodeActivity` which is used to track node actions and can be leveraged for registration state tracking since no dedicated `CampusNode` model exists.
- `app/modules/did/engine.py`: Provides `issue_credential` and identity management needed for `NodeContributionCredential`.
- `app/modules/wallet/services.py`: `WalletService` is available for crediting rewards.

## What's Missing
- `app/modules/network/campus_node.py`: The registration and activation flow for university-level infrastructure is not yet implemented.
- `app/modules/network/university_api.py`: Public endpoints for listing verified universities and their contribution stats are missing.
- `app/modules/network/campus_rewards.py`: The 70/30 reward split logic between operators and university scholarship pools is not implemented.

## What's Broken / Improvements Needed
- The system currently lacks a formal way to verify "Campus" status beyond manual admin intervention via the proposed `activate` endpoint.
- Reward distribution for campus nodes needs to handle two separate recipients (operator and university pool), which requires clear wallet identification.
- `NodeActivity` records will be used to store registration metadata; this should be carefully managed to ensure only the latest active registration is considered.
