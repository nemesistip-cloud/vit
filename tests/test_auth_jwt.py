from datetime import timedelta

from app.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_access_token_round_trip_contains_access_type():
    token = create_access_token({"sub": "user@example.com", "user_id": 7})
    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["user_id"] == 7
    assert payload["type"] == "access"


def test_refresh_token_round_trip_contains_refresh_type():
    token = create_refresh_token({"sub": "user@example.com"})
    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["type"] == "refresh"


def test_invalid_token_returns_none():
    assert decode_token("not-a-valid-token") is None


def test_expired_access_token_returns_none():
    token = create_access_token({"sub": "expired@example.com"}, expires_delta=timedelta(seconds=-1))

    assert decode_token(token) is None


def test_password_hash_verification():
    hashed = hash_password("VitUser@2026!")

    assert verify_password("VitUser@2026!", hashed)
    assert not verify_password("wrong-password", hashed)