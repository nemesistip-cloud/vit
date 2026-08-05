import os
import sys
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# --- Core App Settings ---
APP_NAME: str = "VIT Network"
APP_VERSION: str = "1.1.0"
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def get_int_env(key: str, default: int = 0) -> int:
    """Read an integer from the environment. Accepts default as int (not str)."""
    return int(os.getenv(key, str(default)))

def _clean_redis_url(url: str) -> str:
    if not url: return ""
    if url.startswith("redis://") or url.startswith("rediss://"):
        return url
    return f"redis://{url}"

# Bridge to the new Configuration Framework
def _get_config():
    try:
        from app.core.config.manager import config_manager
        return config_manager.config
    except (ImportError, RuntimeError):
        return None

# Static mirror of the (section, key) -> env var alias mapping defined in
# app/core/config/models.py. This MUST stay a plain dict (no imports from
# app.core.config.models) because app.config is imported very early during
# process bootstrap (before app.core.config.manager.config_manager.load()
# has run), and importing app.core.config.models transitively imports the
# app.core package, which imports app.core.dependencies, which imports back
# into app.config — a circular import that silently breaks mid-bootstrap
# and is easy to reintroduce if this is refactored to look the alias up
# dynamically from the pydantic models instead.
_ENV_ALIASES = {
    ("app", "secret_key"): "SECRET_KEY",
    ("app", "jwt_secret_key"): "JWT_SECRET_KEY",
    ("app", "session_secret"): "SESSION_SECRET",
    ("app", "pytorch_device"): "PYTORCH_DEVICE",
    ("app", "bootstrap_match_months"): "BOOTSTRAP_MATCH_MONTHS",
    ("db", "url"): "DATABASE_URL",
    ("db", "pool_size"): "DB_POOL_SIZE",
    ("db", "max_overflow"): "DB_MAX_OVERFLOW",
    ("db", "echo"): "DB_ECHO",
    ("redis", "url"): "REDIS_URL",
    ("redis", "pool_size"): "REDIS_POOL_SIZE",
    ("ai", "isports_api_key"): "ISPORTS_API_KEY",
    ("ai", "football_data_api_key"): "FOOTBALL_DATA_API_KEY",
    ("ai", "the_odds_api_key"): "ODDS_API_KEY",
    ("ai", "the_sportsdb_api_key"): "THESPORTSDB_API_KEY",
    ("ai", "embedding_model"): "EMBEDDING_MODEL",
    ("ai", "embedding_dim"): "EMBEDDING_DIM",
    ("ai", "embedding_cache_ttl"): "EMBEDDING_CACHE_TTL",
    ("ai", "max_predictions_per_day"): "MAX_PREDICTIONS_PER_DAY",
    # Base L2 removed — VIT Chain is now a standalone service (Chain ID 7764)
    ("external", "resend_api_key"): "RESEND_API_KEY",
    ("external", "paystack_secret_key"): "PAYSTACK_SECRET_KEY",
    ("external", "flw_secret_key"): "FLW_SECRET_KEY",
    ("external", "pi_app_id"): "PI_APP_ID",
    ("external", "pi_app_secret"): "PI_APP_SECRET",
    ("external", "pi_webhook_secret"): "PI_WEBHOOK_SECRET",
    ("external", "pi_sandbox_mode"): "PI_SANDBOX_MODE",
    ("external", "telegram_bot_token"): "TELEGRAM_BOT_TOKEN",
    ("external", "telegram_chat_id"): "TELEGRAM_CHAT_ID",
    ("external", "gcp_project_id"): "GCP_PROJECT_ID",
    ("external", "google_application_credentials"): "GOOGLE_APPLICATION_CREDENTIALS",
    ("external", "google_application_credentials_json"): "GOOGLE_APPLICATION_CREDENTIALS_JSON",
    ("external", "smtp_pass"): "SMTP_PASS",
    ("external", "paystack_webhook_secret"): "PAYSTACK_WEBHOOK_SECRET",
    ("tachyon", "data_shards"): "TACHYON_DATA_SHARDS",
    ("tachyon", "parity_shards"): "TACHYON_PARITY_SHARDS",
    ("tachyon", "encryption_key"): "TACHYON_ENCRYPTION_KEY",
    ("tachyon", "s3_api_key"): "TACHYON_S3_API_KEY",
}

def _resolve_env_alias(section: str, key: str) -> Optional[str]:
    """Look up the real environment variable name for a given section/key,
    so the pre-config-load fallback in get_val() reads the correct env var
    instead of guessing `key.upper()` (which is wrong for almost every
    field, e.g. section="db", key="url" -> "URL" instead of
    "DATABASE_URL")."""
    return _ENV_ALIASES.get((section, key))

def get_val(section: str, key: str, default: Any = None) -> Any:
    cfg = _get_config()
    if cfg:
        try:
            section_obj = getattr(cfg, section)
            val = getattr(section_obj, key, default)
            if hasattr(val, "get_secret_value"):
                return val.get_secret_value()
            return val
        except AttributeError:
            return default
    # Config not loaded yet (e.g. this module is being imported before
    # kernel.boot() runs config_manager.load()) — fall back to reading the
    # real environment variable directly via its known alias.
    env_name = _resolve_env_alias(section, key) or key.upper()
    return os.getenv(env_name, default)

# Redefine legacy constants
SECRET_KEY: str = get_val("app", "secret_key", "dev-secret-key")
JWT_SECRET_KEY: str = get_val("app", "jwt_secret_key", "dev-jwt-secret")
SESSION_SECRET: str = get_val("app", "session_secret", "")
DATABASE_URL: str = get_val("db", "url", "sqlite+aiosqlite:///./vit.db")
REDIS_URL: str = _clean_redis_url(get_val("redis", "url", ""))

FOOTBALL_DATA_API_KEY: str = get_val("ai", "football_data_api_key", "")
ISPORTS_API_KEY: str = get_val("ai", "isports_api_key", "")
THE_ODDS_API_KEY: str = get_val("ai", "the_odds_api_key", "")
ODDS_API_KEY: str = THE_ODDS_API_KEY
THESPORTSDB_API_KEY: str = get_val("ai", "the_sportsdb_api_key", "3")

PAYSTACK_SECRET_KEY: str = get_val("external", "paystack_secret_key", "")
FLW_SECRET_KEY: str = get_val("external", "flw_secret_key", "")
PI_APP_ID: str = get_val("external", "pi_app_id", "")
PI_SANDBOX_MODE: str = str(get_val("external", "pi_sandbox_mode", "true")).lower()

RESEND_API_KEY: str = get_val("external", "resend_api_key", "")
TELEGRAM_BOT_TOKEN: str = get_val("external", "telegram_bot_token", "")
TELEGRAM_CHAT_ID: str = get_val("external", "telegram_chat_id", "")

MAX_PREDICTIONS_PER_DAY: int = int(get_val("ai", "max_predictions_per_day", 20))
PYTORCH_DEVICE: str = get_val("app", "pytorch_device", "cpu")
BOOTSTRAP_MATCH_MONTHS: int = int(get_val("app", "bootstrap_match_months", 6))

# Base L2 removed. VIT Chain standalone: VIT_CHAIN_URL points to vitnetwork/vit-chain.
VIT_CHAIN_URL: str = get_val("chain", "vit_chain_url", "")

ENABLE_SCRAPING: bool = os.getenv("ENABLE_SCRAPING", "false").lower() == "true"
AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "true").lower() == "true"
API_KEY: str = os.getenv("API_KEY", "")

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Set RATE_LIMIT_ENABLED=false to disable globally (e.g. during load testing).
# Defaults to true in production; the middleware also bypasses /health, /docs,
# /static, and websocket paths regardless of this flag.
RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

# ── CORS ──────────────────────────────────────────────────────────────────────
# CORS_ALLOWED_ORIGINS: comma-separated list of allowed origins in production.
# Example: "https://vit.network,https://www.vit.network"
# Leave empty (or unset) to default to "*" in development only.
# In production (ENVIRONMENT=production) an explicit list is required;
# the middleware will log a warning if "*" is used in production.
CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "")

def print_config_status() -> None:
    try:
        from app.core.config.manager import config_manager
        diag = config_manager.get_diagnostics()
    except ImportError:
        return

    if diag.get("status") != "loaded":
        return

    cfg = config_manager.config
    print(f"\n{'='*55}")
    print(f"  {cfg.app.name} v{cfg.app.version}")
    print(f"{'='*55}")
    print(f"  ✅ Environment:       {cfg.app.environment.value}")
    print("  ✅ Database:           Configured")
    print(f"  {'✅' if cfg.ai.isports_api_key else '❌'} iSports API:        {'Configured' if cfg.ai.isports_api_key else 'Missing'}")
    print(f"  {'✅' if cfg.ai.football_data_api_key else '❌'} Football API:       {'Configured' if cfg.ai.football_data_api_key else 'Missing'}")
    print(f"  {'✅' if cfg.ai.the_odds_api_key else '❌'} Odds API:           {'Configured' if cfg.ai.the_odds_api_key else 'Missing (odds disabled)'}")
    print(f"  {'✅' if cfg.external.paystack_secret_key else '❌'} Paystack:           {'Configured' if cfg.external.paystack_secret_key else 'Missing (payments disabled)'}")
    print(f"  {'✅' if cfg.external.flw_secret_key else '⚠️ '} Flutterwave/MoMo:  {'Configured' if cfg.external.flw_secret_key else 'Missing (MoMo deposits disabled)'}")
    print(f"  {'✅' if cfg.external.pi_app_id else '⚠️ '} Pi Network:         {'Configured (sandbox)' if cfg.external.pi_app_id and cfg.external.pi_sandbox_mode else 'Configured (mainnet)' if cfg.external.pi_app_id else 'Missing (Pi payments disabled)'}")
    print(f"  {'✅' if cfg.external.resend_api_key else '❌'} RESEND Email:       {'Configured' if cfg.external.resend_api_key else 'Missing (email disabled)'}")
    print(f"  ✅ TheSportsDB:       Always available (key: {cfg.ai.the_sportsdb_api_key})")
    print(f"{'='*55}\n")

GCP_PROJECT_ID = get_val("external", "gcp_project_id", "")
EMBEDDING_MODEL = get_val("ai", "embedding_model", "all-MiniLM-L6-v2")
EMBEDDING_DIM = get_val("ai", "embedding_dim", 384)
TACHYON_DATA_SHARDS = get_val("tachyon", "data_shards", 4)
TACHYON_PARITY_SHARDS = get_val("tachyon", "parity_shards", 2)
VIT_STORAGE_USE_EXTERNAL: bool = os.getenv("VIT_STORAGE_USE_EXTERNAL", "false").lower() == "true"

# Additional legacy flags
ENABLE_ODDS: bool = os.getenv("ENABLE_ODDS", "true").lower() == "true"
ENABLE_PAYMENTS: bool = os.getenv("ENABLE_PAYMENTS", "true").lower() == "true"

REPLIT_DEPLOYMENT: bool = os.getenv("REPL_SLUG") is not None

# ── Phase 0: Service Registry URLs ───────────────────────────────────────────
# Override these env vars when services move hosts — nothing else needs to change.
VIT_GATEWAY_URL: str = os.getenv("VIT_GATEWAY_URL", "")
VIT_AI_URL: str      = os.getenv("VIT_AI_URL",      "")
VIT_STORAGE_URL: str = os.getenv("VIT_STORAGE_URL", "")

# ── Phase 0: Internal Service Auth ────────────────────────────────────────────
# Set to a random 32+ byte string shared across all VIT services.
SERVICE_TOKEN_SECRET: str = os.getenv("SERVICE_TOKEN_SECRET", "")

# Newly discovered missing constants
MAX_STAKE: float = float(os.getenv("MAX_STAKE", "100.0"))
MIN_EDGE_THRESHOLD: float = float(os.getenv("MIN_EDGE_THRESHOLD", "0.02"))
PUBLIC_APP_URL: str = os.getenv("PUBLIC_APP_URL", "https://vit.network")
GOOGLE_APPLICATION_CREDENTIALS: str = get_val("external", "google_application_credentials", "")

# UI branding constants
APP_TAGLINE: str = os.getenv("APP_TAGLINE", "AI Intelligence & Blockchain Super App")
APP_SHORT_NAME: str = os.getenv("APP_SHORT_NAME", "VIT")

# Service discovery and additional missing constants
TELEGRAM_BOT_USERNAME: str = os.getenv("TELEGRAM_BOT_USERNAME", "VITNetworkBot")
SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@vit.network")
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.resend.com")
SMTP_PASS: str = get_val("external", "smtp_pass", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "resend")
GOOGLE_APPLICATION_CREDENTIALS_JSON: str = get_val("external", "google_application_credentials_json", "")
EMBEDDING_CACHE_TTL: int = int(get_val("ai", "embedding_cache_ttl", 3600))
PI_APP_SECRET: str = get_val("external", "pi_app_secret", "")
PI_WEBHOOK_SECRET: str = get_val("external", "pi_webhook_secret", "")
REPLIT_DEV_DOMAIN: str = os.getenv("REPL_SLUG", "") # Simplified
PAYSTACK_WEBHOOK_SECRET: str = get_val("external", "paystack_webhook_secret", "")
USDT_MIN_CONFIRMATIONS: int = int(os.getenv("USDT_MIN_CONFIRMATIONS", "3"))
