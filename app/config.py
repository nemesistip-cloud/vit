"""app/config.py — Single source of truth for all runtime configuration.

Every environment variable the application reads lives here. Callers import

# GCS Storage
GCS_BUCKET_NAME = get_env("GCS_BUCKET_NAME", "")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
GCS_PROJECT_ID = get_env("GCS_PROJECT_ID", "")
GOOGLE_APPLICATION_CREDENTIALS = get_env("GOOGLE_APPLICATION_CREDENTIALS", "")
named constants (e.g. from app.config import REDIS_URL) so a change to
the env-var name only needs updating in one place.

Load order:
  1. Real environment variables (set by Replit Secrets / OS)
  2. .env file on disk (override=False — secrets always win)
  3. Hardcoded defaults defined in this file

Never import os.getenv directly in other modules — always use this file.
"""

import os
import sys
import secrets
from pathlib import Path
from dotenv import load_dotenv


# ── .env loading ───────────────────────────────────────────────────────────────
# Resolve the .env file one directory above this file (the project root).
# override=False means existing OS/Replit environment variables are NOT
# replaced by .env values — secrets set via Replit Secrets always take priority.
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=DOTENV_PATH, override=False)


# ── Environment reader ─────────────────────────────────────────────────────────

def get_env(name: str, default: str = "") -> str:
    """Read a configuration value, preferring live environment over .env file.

    Args:
        name:    The environment variable name, e.g. "DATABASE_URL".
        default: Value to return when the variable is absent entirely.

    Returns:
        The string value of the variable, or default if unset/empty.
    """
    # os.environ.get() returns None for missing keys; the second os.getenv()
    # reads whatever python-dotenv loaded from the .env file.
    value = os.environ.get(name)
    if value:
        return value
    return os.getenv(name, default) or default


def get_bool_env(name: str, default: str = "false") -> bool:
    """Read a boolean-like env var with sane defaults."""
    value = get_env(name, default).strip().lower()
    return value in ("1", "true", "yes", "on")


def get_int_env(name: str, default: str = "0") -> int:
    """Read an integer env var with fallback for invalid values."""
    try:
        return int(get_env(name, default))
    except (TypeError, ValueError):
        return int(default)


# ── JWT / session secret resolution ───────────────────────────────────────────

def _get_secure_secret_key() -> str:
    """Resolve the JWT signing secret from the environment.

    Checks three common variable names so legacy deployments still work:
    - JWT_SECRET_KEY  (preferred, explicit)
    - SECRET_KEY      (common Flask/Django convention)
    - SESSION_SECRET  (Replit's auto-generated app secret)

    In *production* (REPLIT_DEPLOYMENT=1 or ENVIRONMENT=production),
    an unconfigured secret is a critical error, but we log and continue with
    an ephemeral key to avoid crashing the container during startup/build.

    In *development*, a random 48-byte key is generated with a console warning.
    Sessions will not survive restarts, but the app will still run.
    """
    configured = (
        get_env("JWT_SECRET_KEY")
        or get_env("SECRET_KEY")
        or get_env("SESSION_SECRET")
    )
    if configured:
        return configured  # Happy path: a real secret is configured

    # Log critical error but don't hard-crash during import phase in production.
    if get_env("REPLIT_DEPLOYMENT") or get_env("ENVIRONMENT").lower() == "production":
        sys.stderr.write(
            "\n[CRITICAL] JWT_SECRET_KEY is not configured. "
            "Set it in environment variables before deploying. "
            "Using an EPHEMERAL key for now to allow startup.\n"
        )

    # Development/Missing-Secret fallback: warn loudly but continue.
    sys.stderr.write(
        "\n[WARN] JWT_SECRET_KEY is not set. Generating an EPHEMERAL dev key — "
        "all issued tokens will be invalidated on next restart. "
        "Add JWT_SECRET_KEY to environment variables to persist sessions.\n\n"
    )
    return secrets.token_urlsafe(48)


# ── Redis URL sanitiser ────────────────────────────────────────────────────────

def _clean_redis_url(raw: str) -> str:
    """Extract a valid redis(s):// or unix:// URL from a raw env string.

    Handles a common mistake where the Replit Secret is set to the full
    redis-cli shell command instead of just the connection URL, e.g.:

        WRONG:   redis-cli -u redis://user:pass@host:6379
        CORRECT: redis://user:pass@host:6379

    If the raw string already starts with a valid scheme it is returned as-is.
    If no valid scheme is found the raw value is returned unchanged so the
    downstream aioredis.from_url() call produces a clear error message.

    Args:
        raw: The raw value of the REDIS_URL environment variable.

    Returns:
        A clean redis:// / rediss:// / unix:// URL string,
        or an empty string if raw is empty.
    """
    import re as _re
    if not raw:
        return ""
    raw = raw.strip()
    # Search anywhere in the string for a redis URL pattern.
    # rediss:// is the TLS variant; unix:// is a socket path.
    m = _re.search(r"(rediss?://\S+|unix://\S+)", raw)
    if m:
        return m.group(1)  # Return only the URL portion, discarding any CLI flags
    return raw  # Already a bare URL or unrecognised format — pass through


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION IDENTITY — SINGLE SOURCE OF TRUST
# These values are used across the entire ecosystem (API, Email, Frontend, Logs).
# ══════════════════════════════════════════════════════════════════════════════

APP_VERSION: str    = "5.5.0"
APP_NAME: str       = get_env("APP_NAME",       "VIT Network")
APP_SHORT_NAME: str = get_env("APP_SHORT_NAME", "VIT")
APP_TAGLINE: str    = get_env("APP_TAGLINE",    "AI Intelligence & Blockchain Super App")
ADMIN_EMAIL: str    = get_env("ADMIN_EMAIL",    "admin@vit.network")
SUPPORT_EMAIL: str  = get_env("SUPPORT_EMAIL",  "support@vit.network")
LEGAL_EMAIL: str    = get_env("LEGAL_EMAIL",    "legal@vit.network")


# ══════════════════════════════════════════════════════════════════════════════
# PREDICTION / BANKROLL CONSTANTS
# All financial thresholds are expressed as fractions (0–1) of the bankroll.
# Override via env vars to tune aggressiveness without a code change.
# ══════════════════════════════════════════════════════════════════════════════

# Maximum fraction of the bankroll to stake on a single prediction (5% default)
MAX_STAKE: float          = float(get_env("MAX_STAKE",          "0.05"))
# Minimum required edge (probability advantage over implied odds) to recommend a bet
MIN_EDGE_THRESHOLD: float = float(get_env("MIN_EDGE_THRESHOLD", "0.02"))


# ══════════════════════════════════════════════════════════════════════════════
# ML / MODEL LIMITS
# ══════════════════════════════════════════════════════════════════════════════

# LSTM training guard: caps synthetic sequence generation to avoid OOM on large datasets.
# The LSTM model is excluded from training above this sequence count.
LSTM_MAX_TRAINING_SEQS: int = int(get_env("LSTM_MAX_TRAINING_SEQS", "2000"))


# ══════════════════════════════════════════════════════════════════════════════
# NETWORK PORTS
# Informational only — actual binding is controlled by the start command.
# ══════════════════════════════════════════════════════════════════════════════

BACKEND_PORT: int  = get_int_env("BACKEND_PORT",  "8000")
FRONTEND_PORT: int = get_int_env("FRONTEND_PORT", "5000")


# ══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT / DEPLOYMENT
# ══════════════════════════════════════════════════════════════════════════════

ENVIRONMENT: str         = get_env("ENVIRONMENT", "development")
REPLIT_DEPLOYMENT: bool  = bool(get_env("REPLIT_DEPLOYMENT", ""))
REPLIT_DEV_DOMAIN: str   = get_env("REPLIT_DEV_DOMAIN", "")
REPL_SLUG: str           = get_env("REPL_SLUG", "")
PUBLIC_APP_URL: str      = get_env("PUBLIC_APP_URL", "")
FRONTEND_URL: str        = get_env("FRONTEND_URL", PUBLIC_APP_URL or "")

AUTH_ENABLED: bool       = get_bool_env("AUTH_ENABLED")
RATE_LIMIT_ENABLED: bool = get_bool_env("RATE_LIMIT_ENABLED", "true")
ENABLE_SCRAPING: bool    = get_bool_env("ENABLE_SCRAPING", "false")
ENABLE_ODDS: bool        = get_bool_env("ENABLE_ODDS", "true")
ENABLE_SYNTHETIC_FIXTURES: bool = get_bool_env("ENABLE_SYNTHETIC_FIXTURES", "false")

ADMIN_EMAIL: str         = get_env("ADMIN_EMAIL", "admin@vit.network")
ADMIN_USERNAME: str      = get_env("ADMIN_USERNAME", "vit_admin")
ADMIN_PASSWORD: str      = get_env("ADMIN_PASSWORD", "")

SMTP_FROM: str           = get_env("SMTP_FROM", "VIT Network <noreply@vit.network>")
SMTP_HOST: str           = get_env("SMTP_HOST", "")
SMTP_PORT: int           = get_int_env("SMTP_PORT", "587")
SMTP_USER: str           = get_env("SMTP_USER", "")
SMTP_PASS: str           = get_env("SMTP_PASS", "")

API_KEY: str              = get_env("API_KEY", "")
ORACLE_API_KEY: str       = get_env("ORACLE_API_KEY", "")
TELEGRAM_BOT_USERNAME: str       = get_env("TELEGRAM_BOT_USERNAME", "VITSportsBot")
USDT_MIN_CONFIRMATIONS: int      = get_int_env("USDT_MIN_CONFIRMATIONS", "3")

# ══════════════════════════════════════════════════════════════════════════════
# SECURITY KEYS
# JWT_SECRET_KEY is used to sign/verify all access tokens.
# SECRET_KEY is the Flask-style fallback used for session cookies elsewhere.
# Both resolve via _get_secure_secret_key() which enforces prod safety.
# ══════════════════════════════════════════════════════════════════════════════

SECRET_KEY: str     = get_env("SECRET_KEY") or _get_secure_secret_key()
JWT_SECRET_KEY: str = get_env("JWT_SECRET_KEY") or SECRET_KEY


# ══════════════════════════════════════════════════════════════════════════════
# EXTERNAL API KEYS
# Google Auth
GOOGLE_CLIENT_ID: str        = get_env("GOOGLE_CLIENT_ID", "")

# All empty-string defaults make missing keys safe to detect with if KEY:.
# ══════════════════════════════════════════════════════════════════════════════

# Football-Data.org — primary fixture + live score source (requires paid plan)
FOOTBALL_DATA_API_KEY: str = get_env("FOOTBALL_DATA_API_KEY", "")

# iSportsAPI.com — robust sports data provider (primary fallback/alternative)
ISPORTS_API_KEY: str = get_env("ISPORTS_API_KEY", "")

# The Odds API — bookmaker odds feed for CLV tracking and arbitrage detection
# Supports both var names for backward compatibility with older deployments
THE_ODDS_API_KEY: str      = get_env("THE_ODDS_API_KEY", "") or get_env("ODDS_API_KEY", "")
ODDS_API_KEY: str          = THE_ODDS_API_KEY

# Paystack — NGN (Nigerian Naira) payment gateway for African users
PAYSTACK_SECRET_KEY: str     = get_env("PAYSTACK_SECRET_KEY", "")
PAYSTACK_WEBHOOK_SECRET: str = get_env("PAYSTACK_WEBHOOK_SECRET", "")

# Stripe — USD/international subscription payments
STRIPE_SECRET_KEY: str        = get_env("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET: str    = get_env("STRIPE_WEBHOOK_SECRET", "")


# Redis — optional; enables distributed rate limiting, caching, and Celery tasks.
# Sanitised by _clean_redis_url() to handle malformed CLI-style env values.
REDIS_URL: str             = _clean_redis_url(get_env("REDIS_URL", ""))

DATABASE_URL: str          = get_env("VIT_DATABASE_URL", "") or get_env("DATABASE_URL", "") or "sqlite+aiosqlite:///./vit.db"

# Resend.com — transactional email (welcome, password reset, alerts)
RESEND_API_KEY: str        = get_env("RESEND_API_KEY", "")
TELEGRAM_BOT_TOKEN: str    = get_env("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str      = get_env("TELEGRAM_CHAT_ID", "")

# TheSportsDB — free fixture source (fallback when Football-Data.org is unavailable)
# Default key "3" is the public demo key; replace with a paid key for production.
THESPORTSDB_API_KEY: str   = get_env("THESPORTSDB_API_KEY", "3")

# Maximum number of AI predictions a single user can request per calendar day.
# Enforced in-memory by app/core/rate_limit.py (resets on restart).
MAX_PREDICTIONS_PER_DAY: int = int(get_env("MAX_PREDICTIONS_PER_DAY", "20"))

# PyTorch device — force CPU to avoid CUDA errors on CPU-only hosts.
# Set PYTORCH_DEVICE=cuda in the environment only if a GPU is confirmed available.
PYTORCH_DEVICE: str = get_env("PYTORCH_DEVICE", "cpu")

# Number of months of historical fixtures to backfill on first startup.
BOOTSTRAP_MATCH_MONTHS: int = int(get_env("BOOTSTRAP_MATCH_MONTHS", "6"))


# ══════════════════════════════════════════════════════════════════════════════
# BLOCKCHAIN / WEB3 CONFIGURATION
# BASE L2 (chain_id=8453) is the default target network.
# Override via env vars to point at a different RPC or contract.
# ══════════════════════════════════════════════════════════════════════════════

BASE_CHAIN_ID: int = get_int_env("BASE_CHAIN_ID", "8453")
BASE_RPC_URL: str = get_env(
    "BASE_RPC_URL",
    "https://mainnet.base.org",
)
VITCOIN_CONTRACT_ADDRESS: str = get_env("VITCOIN_CONTRACT_ADDRESS", "")


# ── Startup Status Banner ──────────────────────────────────────────────────────

def print_config_status() -> None:
    """Print a human-readable configuration status table at server startup.

    Each row shows whether the service's key is present (✅), missing (❌),
    or optional but absent (⚠️). This lets developers spot missing secrets
    immediately without reading environment documentation.
    """
    # Detect whether a real JWT secret is in the environment (vs ephemeral dev key)
    jwt_from_env = bool(get_env("JWT_SECRET_KEY") or get_env("SECRET_KEY") or get_env("SESSION_SECRET"))

    # Settlement mode determines where match results are fetched from:
    # iSports (primary), Football-Data (secondary), or TheSportsDB (tertiary/free)
    football_key = FOOTBALL_DATA_API_KEY
    isports_key = ISPORTS_API_KEY

    if isports_key:
        settle_mode = "iSports API (primary)"
    elif football_key:
        settle_mode = "Football-Data.org (secondary)"
    else:
        settle_mode = "TheSportsDB (free/fallback)"

    print(f"\n{'='*55}")
    print(f"  {APP_NAME} v{APP_VERSION}")
    print(f"{'='*55}")
    print(f"  {'✅' if jwt_from_env else '⚠️ '} JWT/Secret Key:     {'Configured' if jwt_from_env else 'EPHEMERAL DEV KEY — add JWT_SECRET_KEY'}")
    print(f"  ✅ Database:           Configured")  # SQLite always works; Postgres when DATABASE_URL is set
    print(f"  {'✅' if isports_key else '❌'} iSports API:        {'Configured' if isports_key else 'Missing'}")
    print(f"  {'✅' if football_key else '❌'} Football API:       {'Configured' if football_key else 'Missing'}")
    print(f"  {'✅' if THE_ODDS_API_KEY else '❌'} Odds API:           {'Configured' if THE_ODDS_API_KEY else 'Missing (odds disabled)'}")
    print(f"  {'✅' if PAYSTACK_SECRET_KEY else '❌'} Paystack:           {'Configured' if PAYSTACK_SECRET_KEY else 'Missing (NGN payments disabled)'}")
    print(f"  {'✅' if STRIPE_SECRET_KEY else '❌'} Stripe:             {'Configured' if STRIPE_SECRET_KEY else 'Missing (USD payments disabled)'}")
    print(f"  {'✅' if RESEND_API_KEY else '❌'} RESEND Email:       {'Configured' if RESEND_API_KEY else 'Missing (email disabled)'}")
    print(f"  ✅ TheSportsDB:       Always available (free key)")
    print(f"  ✅ Settlement mode:   {settle_mode}")
    print(f"  {'✅' if REDIS_URL else '⚠️ '} Redis:              {'Configured' if REDIS_URL else 'Missing (in-memory rate limiting only)'}")
    print(f"{'='*55}\n")

# GCS Storage
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
GCS_PROJECT_ID = os.getenv("GCS_PROJECT_ID", "")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# GCS Storage
