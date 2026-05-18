import os
import sys
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load .env without overriding existing environment variables.
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=DOTENV_PATH, override=False)


def get_env(name: str, default: str = "") -> str:
    """Read environment variables from os.environ first, then fallback to .env values."""
    value = os.environ.get(name)
    if value:
        return value
    return os.getenv(name, default) or default


def _get_secure_secret_key() -> str:
    """Resolve JWT signing secret from Replit Secrets / env only.

    Checks JWT_SECRET_KEY, SECRET_KEY, and SESSION_SECRET (Replit-managed).
    In dev, an ephemeral key is generated and a warning is printed.
    """
    configured = (
        get_env("JWT_SECRET_KEY")
        or get_env("SECRET_KEY")
        or get_env("SESSION_SECRET")
    )
    if configured:
        return configured
    if get_env("REPLIT_DEPLOYMENT") or get_env("ENVIRONMENT").lower() == "production":
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured. Set it in Replit Secrets before deploying."
        )
    sys.stderr.write(
        "\n[WARN] JWT_SECRET_KEY is not set. Generating an EPHEMERAL dev key — "
        "all issued tokens will be invalidated on next restart. "
        "Add JWT_SECRET_KEY to Replit Secrets to persist sessions.\n\n"
    )
    return secrets.token_urlsafe(48)


# ── Application version (single source of truth) ──────────────────────
APP_VERSION: str = "5.0.0"

# ── Application branding ──────────────────────────────────────────────
APP_NAME: str       = get_env("APP_NAME",       "Value Intelligence Trust (VIT)")
APP_SHORT_NAME: str = get_env("APP_SHORT_NAME", "VIT")
APP_TAGLINE: str    = get_env("APP_TAGLINE",    "Where Value, Intelligence, and Trust Converge")
ADMIN_EMAIL: str    = get_env("ADMIN_EMAIL",    "admin@vit.network")
SUPPORT_EMAIL: str  = get_env("SUPPORT_EMAIL",  "support@vit.network")
LEGAL_EMAIL: str    = get_env("LEGAL_EMAIL",    "legal@vit.network")

# ── Prediction / bankroll constants (override via env vars) ────────────
MAX_STAKE: float          = float(get_env("MAX_STAKE",           "0.05"))
MIN_EDGE_THRESHOLD: float = float(get_env("MIN_EDGE_THRESHOLD",  "0.02"))

# ── LSTM training guard (prevents OOM on large synthetic datasets) ─────
LSTM_MAX_TRAINING_SEQS: int = int(get_env("LSTM_MAX_TRAINING_SEQS", "2000"))

# ── Ports (for reference; actual binding uses env vars in start.sh) ────
BACKEND_PORT: int  = int(get_env("BACKEND_PORT",  "8000"))
FRONTEND_PORT: int = int(get_env("FRONTEND_PORT", "5000"))

# ── Security keys ──────────────────────────────────────────────────────
SECRET_KEY: str     = get_env("SECRET_KEY") or _get_secure_secret_key()
JWT_SECRET_KEY: str = get_env("JWT_SECRET_KEY") or SECRET_KEY

# ── External API keys ─────────────────────────────────────────────────
FOOTBALL_DATA_API_KEY: str = get_env("FOOTBALL_DATA_API_KEY", "")
THE_ODDS_API_KEY: str      = get_env("THE_ODDS_API_KEY", "") or get_env("ODDS_API_KEY", "")
PAYSTACK_SECRET_KEY: str   = get_env("PAYSTACK_SECRET_KEY",   "")
STRIPE_SECRET_KEY: str     = get_env("STRIPE_SECRET_KEY",     "")
CLAUDE_API_KEY: str        = get_env("CLAUDE_API_KEY",        "")
GEMINI_API_KEY: str        = get_env("GEMINI_API_KEY",        "")
OPENAI_API_KEY: str        = get_env("OPENAI_API_KEY",        "")
REDIS_URL: str             = get_env("REDIS_URL",             "")
RESEND_API_KEY: str        = get_env("RESEND_API_KEY",        "")
THESPORTSDB_API_KEY: str   = get_env("THESPORTSDB_API_KEY",   "3")
MAX_PREDICTIONS_PER_DAY: int = int(get_env("MAX_PREDICTIONS_PER_DAY", "20"))


def print_config_status() -> None:
    """Print a concise config status banner on startup."""
    jwt_from_env = bool(get_env("JWT_SECRET_KEY") or get_env("SECRET_KEY") or get_env("SESSION_SECRET"))
    football_key = FOOTBALL_DATA_API_KEY
    settle_mode  = "Football-Data.org (live)" if football_key else "TheSportsDB (live, free)"

    print(f"\n{'='*55}")
    print(f"  {APP_NAME} v{APP_VERSION}")
    print(f"{'='*55}")
    print(f"  {'✅' if jwt_from_env else '⚠️ '} JWT/Secret Key:     {'Configured (Replit Secret)' if jwt_from_env else 'EPHEMERAL DEV KEY — add JWT_SECRET_KEY'}")
    print(f"  {'✅' if get_env('DATABASE_URL') else '✅'} Database:           Configured")
    print(f"  {'✅' if football_key else '❌'} Football API:       {'Configured' if football_key else 'Missing (live data disabled)'}")
    print(f"  {'✅' if THE_ODDS_API_KEY else '❌'} Odds API:           {'Configured' if THE_ODDS_API_KEY else 'Missing (odds disabled)'}")
    print(f"  {'✅' if PAYSTACK_SECRET_KEY else '❌'} Paystack:           {'Configured' if PAYSTACK_SECRET_KEY else 'Missing (NGN payments disabled)'}")
    print(f"  {'✅' if STRIPE_SECRET_KEY else '❌'} Stripe:             {'Configured' if STRIPE_SECRET_KEY else 'Missing (USD payments disabled)'}")
    print(f"  {'✅' if CLAUDE_API_KEY else '❌'} Claude AI:          {'Configured' if CLAUDE_API_KEY else 'Missing (AI insights disabled)'}")
    print(f"  {'✅' if GEMINI_API_KEY else '❌'} Gemini AI:          {'Configured' if GEMINI_API_KEY else 'Missing (AI insights disabled)'}")
    print(f"  {'✅' if RESEND_API_KEY else '❌'} Resend Email:       {'Configured' if RESEND_API_KEY else 'Missing (email disabled)'}")
    print(f"  ✅ TheSportsDB:       Always available (free key)")
    print(f"  ✅ Settlement mode:   {settle_mode}")
    print(f"  {'✅' if REDIS_URL else '⚠️ '} Redis:              {'Configured' if REDIS_URL else 'Missing (in-memory rate limiting only)'}")
    print(f"{'='*55}\n")
