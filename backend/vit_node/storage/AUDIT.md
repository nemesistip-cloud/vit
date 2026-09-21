# AUDIT - vit_node/storage

## Current State
- `vit_node/config.py`, `vit_node/keystore.py`, and `vit_node/identity.py` are implemented.
- `vit_node/storage/` directory created, but empty.

## Missing Files
- `vit_node/storage/__init__.py`
- `vit_node/storage/gdrive.py`
- `vit_node/storage/agent.py`
- `vit_node/storage/challenge.py`
- `vit_node/storage/monitor.py`

## Dependencies Check
- `google-auth-oauthlib` is not declared in `pyproject.toml`. Add it if this node integration is enabled.
- `google-api-python-client` is declared in `pyproject.toml`.
- `tachyon/core/erasure.py` exists for `ReedSolomonCodec`.

## Hard Constraints Verification
- All new files must use `AppError` from `app.core.errors`.
- No `os.getenv()`; use `get_env` from `app.config`.
- No `asyncio.create_task` in route handlers (not applicable here as this is a client agent, but good to keep in mind).
