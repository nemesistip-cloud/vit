import pytest

from app.api.routes.storage_nodes import normalize_storage_credentials


def test_normalize_storage_credentials_accepts_google_drive_oauth():
    creds = normalize_storage_credentials(
        "gdrive",
        {
            "access_token": " tok-1 ",
            "refresh_token": " tok-2 ",
        },
    )

    assert creds == {
        "access_token": "tok-1",
        "refresh_token": "tok-2",
    }


def test_normalize_storage_credentials_rejects_unknown_provider():
    with pytest.raises(ValueError):
        normalize_storage_credentials("not-a-provider", {"token": "abc"})


def test_normalize_storage_credentials_keeps_json_values_for_service_accounts():
    raw = {
        "service_account_json": '{"type": "service_account"}',
        "access_token": "  "
    }

    creds = normalize_storage_credentials("gdrive", raw)

    assert creds["service_account_json"] == '{"type": "service_account"}'
    assert "access_token" not in creds
