"""app/core/errors.py — Unified error handling for the VIT API.

All API error responses flow through this module so the JSON shape is
consistent across every route and middleware:

    {
        "error": {
            "code":       "rate_limit_exceeded",   # machine-readable slug
            "message":    "Rate limit exceeded.",  # human-readable explanation
            "status_code": 429,
            "request_id": "abc123",                # from X-Request-ID header
            "details":    { ... }                  # optional extra context
        }
    }

Usage:
    from app.core.errors import AppError, error_response

    # Raise inside a route — caught by the global exception handler in main.py:
    raise AppError("Prediction limit reached", status_code=429, code="prediction_limit")

    # Return a JSONResponse directly (useful inside middleware):
    return error_response(request=request, status_code=403, code="forbidden", message="...")
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from starlette.responses import JSONResponse


# ── Exception class ────────────────────────────────────────────────────────────

class AppError(Exception):
    """Domain exception that carries HTTP metadata alongside a message.

    Raise this anywhere in the application. The global exception handler
    registered in ``main.py`` converts it into a structured JSON response
    using ``error_response()``.

    Args:
        message:     Human-readable description of what went wrong.
        status_code: HTTP status code to send to the client (default 400).
        code:        Short machine-readable slug for the client to ``switch`` on.
        details:     Optional dict of extra context (e.g. field-level errors).

    Example::

        raise AppError(
            "Insufficient VITCoin balance",
            status_code=402,
            code="insufficient_balance",
            details={"required": 500, "available": 120},
        )
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "app_error",
        details: Any | None = None,
    ) -> None:
        self.message     = message
        self.status_code = status_code
        self.code        = code
        self.details     = details
        super().__init__(message)


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_request_id(request: Request) -> str:
    """Return the request-scoped ID injected by LoggingMiddleware.

    Falls back to ``"unknown"`` when called outside the middleware chain
    (e.g. in unit tests that create a bare Request object).
    """
    return getattr(request.state, "request_id", None) or "unknown"


def error_payload(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    """Build the canonical error JSON dict without sending it.

    Useful when you need the dict itself (e.g. to log it or embed it in
    a larger response) rather than a full ``JSONResponse``.

    Args:
        request:     Incoming FastAPI/Starlette request (needed for request_id).
        status_code: HTTP status that will be sent to the client.
        code:        Machine-readable error slug (e.g. ``"not_found"``).
        message:     Human-readable description.
        details:     Optional extra data included under ``error.details``.

    Returns:
        A dict shaped as ``{"error": {"code": ..., "message": ..., ...}}``.
    """
    payload: dict[str, Any] = {
        "error": {
            "code":        code,
            "message":     message,
            "status_code": status_code,
            "request_id":  get_request_id(request),
        }
    }
    # Only include the details key when there is something to show —
    # avoids cluttering responses with a ``null`` field.
    if details is not None:
        payload["error"]["details"] = details
    return payload


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Return a structured ``JSONResponse`` with standard error shape.

    ``X-Request-ID`` and ``X-Correlation-ID`` are injected by ``RequestIDMiddleware``
    on every response — do not set them here to avoid duplicate header values.
    Any additional ``headers`` (e.g. ``Retry-After``) are merged in.

    Args:
        request:     Incoming request (provides request_id from state).
        status_code: HTTP status code, e.g. 400, 403, 404, 429, 500.
        code:        Machine-readable slug the client can switch on.
        message:     Human-readable error description.
        details:     Optional structured extra context.
        headers:     Extra response headers to add (e.g. ``{"Retry-After": "60"}``).

    Returns:
        A ``JSONResponse`` ready to return from any route or middleware.
    """
    request_id = get_request_id(request)

    # Always set correlation headers so error_response() is self-contained when
    # called outside the ASGI middleware stack (e.g. in unit tests).
    # RequestIDMiddleware checks for existing headers before appending, so these
    # are never duplicated when the response passes through the middleware.
    response_headers = {
        "X-Request-ID":     request_id,
        "X-Correlation-ID": request_id,
    }
    # Merge caller-supplied headers (e.g. Retry-After for 429 responses)
    if headers:
        response_headers.update(headers)

    return JSONResponse(
        status_code=status_code,
        content=error_payload(
            request=request,
            status_code=status_code,
            code=code,
            message=message,
            details=details,
        ),
        headers=response_headers,
    )
