# AUDIT - vit_node (P2P + CLI + Daemon)

## Current State
- `vit_node/config.py`, `vit_node/keystore.py`, `vit_node/identity.py`, and `vit_node/storage/` are implemented.
- `vit_node/network/` and `vit_node/earnings/` directories created, but empty.

## Missing Files
- `vit_node/network/client.py`
- `vit_node/network/gossip.py`
- `vit_node/earnings/tracker.py`
- `vit_node/cli.py`
- `vit_node/daemon.py`

## Dependencies Check
- `websockets` installed.
- `click` installed.
- `tabulate` installed.
- `vit_chain/p2p/protocol.py` exists.

## Hard Constraints Verification
- All new files must use `AppError`.
- No `os.getenv()`.
- CLI commands should be user-friendly and handle exceptions via `AppError` where appropriate.
