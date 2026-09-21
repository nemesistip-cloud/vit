# VIT Network Environment Variables

Comprehensive reference of all environment variables used by the VIT Network (v5.5.0).

## Core Configuration
VAR_NAME | required/optional | default | description
---------|-------------------|---------|------------
APP_NAME | optional | "VIT Network" | Application display name
APP_SHORT_NAME | optional | "VIT" | Application short name used in UI
APP_TAGLINE | optional | "AI Intelligence & Blockchain Super App" | Application tagline
ENVIRONMENT | optional | "development" | execution environment (development/production)
PORT | optional | 10000 | The port the application binds to
PUBLIC_APP_URL | optional | "" | Canonical public URL of the API
FRONTEND_URL | optional | "" | Public URL of the frontend (defaults to PUBLIC_APP_URL)
DATABASE_URL | optional | sqlite | Postgres or SQLite connection string
REDIS_URL | optional | "" | Redis connection string (required for Celery/Distributed caching)
LOG_LEVEL | optional | "INFO" | Standard logging level
JWT_SECRET_KEY | required (prod) | random | Secret for signing JWT access tokens
SECRET_KEY | optional | random | Flask-style fallback secret key

## Security & Auth
VAR_NAME | required/optional | default | description
---------|-------------------|---------|------------
AUTH_ENABLED | optional | "false" | Global toggle for API authentication
RATE_LIMIT_ENABLED | optional | "true" | Enable/disable API rate limiting
GOOGLE_CLIENT_ID | optional | "" | OAuth2 client ID for Google Auth
ADMIN_USERNAME | optional | "vit_admin" | Initial admin username
ADMIN_PASSWORD | required (prod) | random | Initial admin password
ADMIN_EMAIL | optional | "admin@vit.network" | Initial admin email address
GH_TOKEN | optional | "" | GitHub Personal Access Token for git sync features

## AI & ML Engine
VAR_NAME | required/optional | default | description
---------|-------------------|---------|------------
USE_REAL_ML_MODELS | optional | "false" | Toggle between mock and real ML inference
ENABLED_MODELS | optional | "" | Comma-separated whitelist of ML models (all if empty)
ENABLED_AGENTS | optional | "" | Comma-separated whitelist of AI agents
MAX_PROCESS_RAM_MB | optional | "400" | RAM cap per worker before model eviction
MAX_LOADED_MODELS | optional | "3" | Maximum concurrent model instances in memory
MODEL_CACHE_TTL_SECONDS | optional | "300" | How long to keep inactive models in memory
EMBEDDING_MODEL | optional | "all-MiniLM-L6-v2" | Sentence transformer model for semantic search
EMBEDDING_DIM | optional | "384" | Vector dimensions for embeddings
LSTM_MAX_TRAINING_SEQS | optional | "2000" | Sequence limit for LSTM training
PYTORCH_DEVICE | optional | "cpu" | Torch device (cpu/cuda)
CALIBRATION_METHOD | optional | "isotonic" | Default calibration algorithm (isotonic/sigmoid)

## VIT Chain (L2 Blockchain)
VAR_NAME | required/optional | default | description
---------|-------------------|---------|------------
BASE_CHAIN_ID | optional | "7764" | VIT Chain Network ID (Mirroring Base L2 architecture)
BASE_RPC_URL | optional | "https://mainnet.base.org" | Primary RPC endpoint
VITCOIN_CONTRACT_ADDRESS | optional | "" | ERC-20 contract address for VIT on L2
UNIVERSAL_ORACLE_ADDRESS | optional | "" | UniversalOracle contract for result verification
ORACLE_PRIVATE_KEY | optional | "" | Private key for the system oracle worker
USDT_MIN_CONFIRMATIONS | optional | "3" | Required confirmations for USDT bridging

## Tachyon VESS (Storage)
VAR_NAME | required/optional | default | description
---------|-------------------|---------|------------
TACHYON_STORAGE_ENABLED | optional | "false" | Enable Tachyon backend for large artifacts
TACHYON_DATA_SHARDS | optional | "6" | Reed-Solomon data shard count
TACHYON_PARITY_SHARDS | optional | "3" | Reed-Solomon parity shard count
TACHYON_ENCRYPTION_KEY | optional | "" | Master key for AES-256 shard encryption
TACHYON_ENDPOINT | optional | "" | Internal endpoint for Tachyon coordination
LOCAL_STORAGE_ROOT | optional | "/tmp/vit_storage" | Fallback disk storage path

## External Data APIs
VAR_NAME | required/optional | default | description
---------|-------------------|---------|------------
ISPORTS_API_KEY | optional | "" | Primary API key for iSportsAPI.com
FOOTBALL_DATA_API_KEY | optional | "" | Secondary API key for Football-Data.org
ODDS_API_KEY | optional | "" | API key for The Odds API (odds/CLV tracking)
THESPORTSDB_API_KEY | optional | "3" | Free-tier key for TheSportsDB fallback
RAPIDAPI_KEY | optional | "" | API key for alternative RapidAPI sources

## Payments & Remittance
VAR_NAME | required/optional | default | description
---------|-------------------|---------|------------
PAYSTACK_SECRET_KEY | optional | "" | Paystack private key (NGN payments)
PAYSTACK_WEBHOOK_SECRET | optional | "" | Paystack signature validation secret
FLW_SECRET_KEY | optional | "" | Flutterwave private key (Remittance/MoMo)
FLW_PUBLIC_KEY | optional | "" | Flutterwave public key
FLW_WEBHOOK_SECRET | optional | "" | Flutterwave signature secret
PI_APP_ID | optional | "" | Pi Network Application ID
PI_APP_SECRET | optional | "" | Pi Network Developer Secret
PI_SANDBOX_MODE | optional | "true" | Toggle Pi Sandbox vs Mainnet mode

## Messaging & Notifications
VAR_NAME | required/optional | default | description
---------|-------------------|---------|------------
RESEND_API_KEY | optional | "" | Resend.com API key for transactional emails
SMTP_HOST | optional | "" | SMTP server host (alternative to Resend)
SMTP_PORT | optional | "587" | SMTP server port
SMTP_USER | optional | "" | SMTP username
SMTP_PASS | optional | "" | SMTP password
TELEGRAM_BOT_TOKEN | optional | "" | Auth token for the VIT Telegram bot
TELEGRAM_CHAT_ID | optional | "" | System alert channel ID
TELEGRAM_BOT_USERNAME | optional | "VITSportsBot" | Canonical bot username

## Cloud & Infrastructure
VAR_NAME | required/optional | default | description
---------|-------------------|---------|------------
GCP_PROJECT_ID | optional | "" | Google Cloud Project ID for Secret Manager
GOOGLE_APPLICATION_CREDENTIALS | optional | "" | Path to GCP service account JSON
GOOGLE_APPLICATION_CREDENTIALS_JSON | optional | "" | Inline service account JSON content
RENDER_EXTERNAL_URL | optional | "" | Auto-set by Render (service public URL)
BOOTSTRAP_MATCH_MONTHS | optional | "6" | History range to backfill on cold start
