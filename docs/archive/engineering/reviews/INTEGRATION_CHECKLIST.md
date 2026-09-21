# Session 10.3: Full Platform Integration Checklist

This checklist is for the Session 10.3 operator to ensure all components implemented in Track 10 are fully wired into the main application and environment.

## 1. Router Registration (`main.py`)
Ensure the following routers are registered in `main.py` if not already present.

- [ ] **VIT Chain RPC:**
  ```python
  from vit_chain.rpc.router import router as chain_rpc_router
  app.include_router(chain_rpc_router)
  ```
- [ ] **Tachyon VESS API:**
  ```python
  from tachyon.api.router import router as tachyon_router
  app.include_router(tachyon_router, prefix="/api/tachyon")
  ```

## 2. Environment Variables
Verify the following variables are set in the production environment.

- [ ] `JWT_SECRET_KEY`: High-entropy string for session security.
- [ ] `DATABASE_URL`: Valid PostgreSQL connection string.
- [ ] `REDIS_URL`: Valid Redis connection string.
- [ ] `TACHYON_ENCRYPTION_KEY`: 32-byte hex key for storage encryption.
- [ ] `THESPORTSDB_API_KEY`: Paid key for high-volume fixture ingestion.

## 3. Bootstrap Sequences
Ensure the following initialization calls are added to the `lifespan` or startup sequence.

- [ ] **Tachyon Provider Initialization:**
  ```python
  from tachyon.api.router import initialize_providers
  await initialize_providers(db)
  ```
- [ ] **Blockchain Genesis Sync:**
  Ensure the genesis block is present in the `iot_events` table for VIT Chain height 0.

## 4. Middleware & Dependency Checks
- [ ] **API Key Middleware:** Verify `X-API-Key` is correctly extracted and validated against `PlatformConfig`.
- [ ] **CORS:** Ensure `CORS_ALLOWED_ORIGINS` includes the production frontend domain.

## 5. Background Tasks
- [ ] **Tachyon Verification Worker:** Should be running in the Celery beat schedule or as a supervised task in `main.py`.
- [ ] **Price Index Sync:** Ensure the `vitcoin_pricing_loop` is active.

## 6. SDK Verification
- [ ] Run the Python SDK smoke tests against the live API.
- [ ] Verify the TypeScript SDK (`packages/sdk`) build and export.
