---
name: X-Request-ID header dedup contract
description: How error_response() and RequestIDMiddleware share responsibility for correlation headers without duplication.
---

## The contract

`error_response()` (`app/core/errors.py`) **always** sets `X-Request-ID` and `X-Correlation-ID` in the `JSONResponse` headers.

`RequestIDMiddleware` (`app/api/middleware/request_id.py`) **guards** before appending — it checks `existing = {name.lower() for name, _ in resp_headers}` and only appends if the header is absent.

## Why this split
- Unit tests call `error_response()` directly without the ASGI stack. They assert the headers are present.
- Integration tests pass through middleware. Without the guard, each header appears twice (`"value, value"`), which breaks equality checks like `response.headers["X-Request-ID"] == rid`.
- The previous approach (removing headers from `error_response()`) broke unit tests. The correct fix is the guard in middleware.

## How to apply
- If you add a new header in `error_response()` that the middleware also injects, add a matching guard in `send_wrapper` in `request_id.py`.
- Never remove correlation headers from `error_response()` to "fix" duplication — fix the middleware guard instead.
