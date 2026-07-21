# VIT Network — REST API & OpenAPI Specifications

**Version:** 6.0.0
**Domain:** /docs/api/
**Status:** Spec Approved

---

## 1. Overview & Router Architecture

The VIT Network gateway API is built on FastAPI, serving structured JSON-RPC and RESTful endpoints. All API endpoints are namespaced under the `/api` prefix in `main.py`.

To prevent SPA routing conflicts or broken deep-links:
- If a route does not begin with `/api` or `/explorer`, the server fallbacks to serving the compiled React frontend `index.html`.
- Therefore, frontend API client requests must *always* include the `/api` prefix.

---

## 2. API Router Namespaces & Decorators

API routes are registered in specialized router modules and imported into `main.py` or subsystem initializers.

### 2.1 Standard Route Decorator Pattern
Every mutation endpoint must use explicit Pydantic schemas for input and output validation:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter(prefix="/matches", tags=["matches"])

@router.get("/upcoming", response_model=list[MatchSchema])
async def get_upcoming_matches(db: AsyncSession = Depends(get_db)):
    """Retrieve upcoming scheduled sports matches."""
    # Logic...
```

### 2.2 Security Middleware Gating
- Administrative endpoints (`/api/admin/...`) use the `@require_admin` dependency gate.
- API keys are validated using the `X-API-Key` header mapped by the `APIKeyMiddleware`.

---

## 3. Core API Endpoint Definitions

Below is the OpenAPI outline of the core system routes:

```
/api/
  ├── auth/
  │     ├── register            # POST: Register standard user
  │     ├── login               # POST: Authenticate user (rate-limited)
  │     ├── refresh             # POST: Rotate JWT tokens
  │     └── me                  # GET: Retrieve current active profile
  ├── chain/
  │     ├── rpc                 # POST: JSON-RPC 2.0 (eth_getBalance, etc.)
  │     ├── height              # GET: Get current blockchain block height
  │     └── latest              # GET: Retrieve latest proposed block
  ├── storage/
  │     ├── upload              # POST: Shred and upload file shards
  │     ├── download/{file_id}  # GET: Reassemble and download file shards
  │     └── status              # GET: Retrieve Tachyon network health
  ├── wallet/
  │     ├── balance             # GET: Fetch multi-currency balance
  │     ├── convert             # POST: Convert currency (idempotency key)
  │     └── withdraw            # POST: Trigger withdrawal request
  └── sports/
        ├── competitions        # GET: List the 22 active competitions
        └── sync/status         # GET: Monitor live feed provider status
```

---

## 4. Response Serialization & Error Handling

To prevent FastAPI serialization crashes when database objects contain raw Python exceptions, a recursive cleanup utility (`_clean_non_serializable`) is integrated inside `app/core/errors.py`. This utility translates exception tracebacks or system pointers under the `details` field into clean string representations.

### 4.1 Error Response Schema
```json
{
  "status_code": 400,
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "The requested match could not be retrieved.",
  "details": {
    "resource_id": "4301",
    "timestamp": "2026-07-19T14:22:00Z"
  }
}
```

By standardizing these API specs, developers and AI agents can seamlessly interact with the VIT Network across all programmatic clients.
