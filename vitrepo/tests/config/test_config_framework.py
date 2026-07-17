import pytest
import os
import asyncio
from pydantic import SecretStr
from app.core.config.manager import ConfigurationManager
from app.core.config.models import Environment
from app.core.config.secrets import secrets_manager
from app.core.config.feature_flags import feature_flag_manager

@pytest.fixture(autouse=True)
def setup_env():
    os.environ["SECRET_KEY"] = "test-secret"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
    os.environ["ENVIRONMENT"] = "testing"
    yield
    # Cleanup if needed

@pytest.mark.asyncio
async def test_config_loading_and_validation():
    manager = ConfigurationManager()
    await manager.load()

    assert manager.config.app.environment == Environment.TESTING
    assert manager.config.app.secret_key.get_secret_value() == "test-secret"
    assert manager.config.app.jwt_secret_key.get_secret_value() == "test-jwt-secret"

def test_secrets_redaction():
    secret = SecretStr("my-secret-value")
    redacted = secrets_manager.redact(secret)
    assert redacted == "********"

    data = {"key": secret, "other": "public"}
    redacted_data = secrets_manager.redact(data)
    assert redacted_data["key"] == "********"
    assert redacted_data["other"] == "public"

def test_feature_flags():
    feature_flag_manager.initialize({"FF_NEW_UI": "true", "FEATURE_BETA": "0"})
    assert feature_flag_manager.is_enabled("NEW_UI") is True
    assert feature_flag_manager.is_enabled("BETA") is False
    assert feature_flag_manager.is_enabled("NON_EXISTENT", default=True) is True

@pytest.mark.asyncio
async def test_config_diagnostics():
    manager = ConfigurationManager()
    await manager.load()
    diag = manager.get_diagnostics()

    assert diag["status"] == "loaded"
    assert diag["environment"] == "testing"
    assert "effective_config" in diag
    # Ensure secret is redacted in diagnostics
    assert diag["effective_config"]["app"]["secret_key"] == "********"

@pytest.mark.asyncio
async def test_config_bridge():
    manager = ConfigurationManager()
    await manager.load()

    from app.config import APP_NAME, ENVIRONMENT, get_val
    assert APP_NAME == "VIT Network"
    # Bridge ENVIRONMENT might be loaded at import time, but get_val should be dynamic
    assert get_val("app", "secret_key") == "test-secret"
    assert get_val("app", "environment") == "testing"
