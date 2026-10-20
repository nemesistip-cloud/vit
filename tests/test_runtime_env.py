import os

import pytest


def test_load_runtime_env_reads_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("REDIS_URL=redis://example:6379/0\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REDIS_URL", raising=False)

    from app.config import load_runtime_env

    load_runtime_env()

    assert os.getenv("REDIS_URL") == "redis://example:6379/0"


def test_resolve_chain_mode_defaults_to_external_when_url_is_present(monkeypatch):
    monkeypatch.delenv("VIT_CHAIN_MODE", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("VIT_CHAIN_URL", "https://chain.example")

    from app.config import resolve_chain_mode

    assert resolve_chain_mode() == "external"


def test_production_environment_rejects_default_dev_secrets(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "dev-jwt-secret")

    from app.config import validate_runtime_security
    from app.core.errors import StartupError

    with pytest.raises(StartupError, match="JWT_SECRET_KEY|SECRET_KEY"):
        validate_runtime_security()


def test_runtime_config_prefers_explicit_jwt_secret_over_lazy_defaults(monkeypatch):
    secret = "runtime-jwt-secret-with-at-least-32-characters"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)

    from app.config import get_val

    assert get_val("app", "jwt_secret_key", "fallback") == secret


def test_external_postgres_uses_certificate_verified_tls():
    import ssl
    from app.db.database import _postgres_connect_args

    external_ssl = _postgres_connect_args("db.example.com")["ssl"]

    assert external_ssl.verify_mode == ssl.CERT_REQUIRED
    assert external_ssl.check_hostname is True
    assert _postgres_connect_args("helium") == {}
    assert _postgres_connect_args("localhost") == {}
