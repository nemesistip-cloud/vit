import json
from types import SimpleNamespace

from app.core.errors import AppError, error_payload, error_response, get_request_id


def make_request(request_id="test-request-id"):
    return SimpleNamespace(state=SimpleNamespace(request_id=request_id))


def test_app_error_keeps_structured_fields():
    exc = AppError(
        "Payment provider unavailable",
        status_code=503,
        code="provider_unavailable",
        details={"provider": "stripe"},
    )

    assert exc.message == "Payment provider unavailable"
    assert exc.status_code == 503
    assert exc.code == "provider_unavailable"
    assert exc.details == {"provider": "stripe"}


def test_error_payload_includes_request_id_and_details():
    request = make_request("rid-123")

    payload = error_payload(
        request=request,
        status_code=422,
        code="validation_error",
        message="Invalid input",
        details=[{"field": "email"}],
    )

    assert payload["error"]["request_id"] == "rid-123"
    assert payload["error"]["status_code"] == 422
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == [{"field": "email"}]


def test_error_response_sets_correlation_headers():
    request = make_request("rid-456")

    response = error_response(
        request=request,
        status_code=401,
        code="invalid_token",
        message="Invalid token",
    )
    body = json.loads(response.body)

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == "rid-456"
    assert response.headers["X-Correlation-ID"] == "rid-456"
    assert body["error"]["request_id"] == "rid-456"


def test_get_request_id_falls_back_to_unknown():
    assert get_request_id(SimpleNamespace(state=SimpleNamespace())) == "unknown"