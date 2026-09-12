import hmac
import hashlib
import json
import time
from urllib.parse import urlencode, parse_qsl
import pytest
from app.auth.telegram import validate_telegram_init_data, MAX_AUTH_AGE_SECONDS
from app.config import TELEGRAM_BOT_TOKEN

def create_valid_init_data(bot_token: str, user_dict: dict, auth_date: int = None) -> str:
    if auth_date is None:
        auth_date = int(time.time())

    vals = {
        "auth_date": str(auth_date),
        "user": json.dumps(user_dict),
        "query_id": "AAH123456789",
    }

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(vals.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    vals["hash"] = expected_hash
    return urlencode(vals)

def test_validate_telegram_init_data_success(monkeypatch):
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    monkeypatch.setattr("app.auth.telegram.TELEGRAM_BOT_TOKEN", bot_token)

    user_payload = {"id": 12345678, "first_name": "Jules", "username": "jules_agent"}
    init_data = create_valid_init_data(bot_token, user_payload)

    result = validate_telegram_init_data(init_data)
    assert result is not None
    assert result["id"] == 12345678
    assert result["username"] == "jules_agent"

def test_validate_telegram_init_data_expired(monkeypatch):
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    monkeypatch.setattr("app.auth.telegram.TELEGRAM_BOT_TOKEN", bot_token)

    user_payload = {"id": 12345678, "first_name": "Jules"}
    old_auth_date = int(time.time()) - (MAX_AUTH_AGE_SECONDS + 100)
    init_data = create_valid_init_data(bot_token, user_payload, auth_date=old_auth_date)

    result = validate_telegram_init_data(init_data)
    assert result is None

def test_validate_telegram_init_data_invalid_hash(monkeypatch):
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    monkeypatch.setattr("app.auth.telegram.TELEGRAM_BOT_TOKEN", bot_token)

    user_payload = {"id": 12345678, "first_name": "Jules"}
    init_data = create_valid_init_data(bot_token, user_payload)

    # Tamper with the query string
    vals = dict(parse_qsl(init_data))
    vals["hash"] = "0000000000000000000000000000000000000000000000000000000000000000"
    tampered_init_data = urlencode(vals)

    result = validate_telegram_init_data(tampered_init_data)
    assert result is None
