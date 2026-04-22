from __future__ import annotations

from typing import Any

from fastapi import Request
from starlette.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "app_error",
        details: Any | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or "unknown"


def error_payload(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "status_code": status_code,
            "request_id": get_request_id(request),
        }
    }
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
    request_id = get_request_id(request)
    response_headers = {
        "X-Request-ID": request_id,
        "X-Correlation-ID": request_id,
    }
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