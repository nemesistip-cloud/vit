from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, SecretStr

class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class AppConfig(BaseModel):
    name: str = Field("VIT Network", alias="APP_NAME")
    version: str = Field("1.1.0", alias="APP_VERSION")
    environment: Environment = Field(Environment.DEVELOPMENT, alias="ENVIRONMENT")
    debug: bool = Field(False, alias="DEBUG")
    secret_key: SecretStr = Field(SecretStr("dev-secret-key"), alias="SECRET_KEY")
    jwt_secret_key: SecretStr = Field(SecretStr("dev-jwt-secret"), alias="JWT_SECRET_KEY")
    session_secret: Optional[SecretStr] = Field(None, alias="SESSION_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_ttl_hours: int = Field(1, alias="JWT_TTL_HOURS")
    pytorch_device: str = Field("cpu", alias="PYTORCH_DEVICE")
    bootstrap_match_months: int = Field(6, alias="BOOTSTRAP_MATCH_MONTHS")

class DatabaseConfig(BaseModel):
    url: str = Field("sqlite+aiosqlite:///./vit.db", alias="DATABASE_URL")
    pool_size: int = Field(5, alias="DB_POOL_SIZE")
    max_overflow: int = Field(10, alias="DB_MAX_OVERFLOW")
    echo: bool = Field(False, alias="DB_ECHO")

class RedisConfig(BaseModel):
    url: str = Field("", alias="REDIS_URL")
    pool_size: int = Field(10, alias="REDIS_POOL_SIZE")

class AIConfig(BaseModel):
    isports_api_key: Optional[SecretStr] = Field(None, alias="ISPORTS_API_KEY")
    football_data_api_key: Optional[SecretStr] = Field(None, alias="FOOTBALL_DATA_API_KEY")
    the_odds_api_key: Optional[SecretStr] = Field(None, alias="ODDS_API_KEY")
    the_sportsdb_api_key: str = Field("3", alias="THESPORTSDB_API_KEY")
    embedding_model: str = Field("all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(384, alias="EMBEDDING_DIM")
    embedding_cache_ttl: int = Field(3600, alias="EMBEDDING_CACHE_TTL")
    max_process_ram_mb: int = Field(400, alias="MAX_PROCESS_RAM_MB")
    max_loaded_models: int = Field(3, alias="MAX_LOADED_MODELS")
    model_cache_ttl_seconds: int = Field(300, alias="MODEL_CACHE_TTL_SECONDS")
    max_predictions_per_day: int = Field(20, alias="MAX_PREDICTIONS_PER_DAY")

class BlockchainConfig(BaseModel):
    base_chain_id: int = Field(8453, alias="BASE_CHAIN_ID")
    base_rpc_url: str = Field("https://mainnet.base.org", alias="BASE_RPC_URL")
    vit_chain_id: int = Field(7764, alias="VIT_CHAIN_ID")
    vitcoin_contract_address: str = Field("", alias="VITCOIN_CONTRACT_ADDRESS")
    validator_key: Optional[SecretStr] = Field(None, alias="VIT_VALIDATOR_KEY")
    treasury_private_key: Optional[SecretStr] = Field(None, alias="VIT_TREASURY_PRIVATE_KEY")
    bootstrap_ws_url: str = Field("wss://vit.network/api/chain/peer", alias="VIT_BOOTSTRAP_WS_URL")

class ExternalServicesConfig(BaseModel):
    resend_api_key: Optional[SecretStr] = Field(None, alias="RESEND_API_KEY")
    paystack_secret_key: Optional[SecretStr] = Field(None, alias="PAYSTACK_SECRET_KEY")
    flw_secret_key: Optional[SecretStr] = Field(None, alias="FLW_SECRET_KEY")
    pi_app_id: Optional[str] = Field(None, alias="PI_APP_ID")
    pi_app_secret: Optional[SecretStr] = Field(None, alias="PI_APP_SECRET")
    pi_webhook_secret: Optional[SecretStr] = Field(None, alias="PI_WEBHOOK_SECRET")
    pi_sandbox_mode: bool = Field(True, alias="PI_SANDBOX_MODE")
    telegram_bot_token: Optional[SecretStr] = Field(None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(None, alias="TELEGRAM_CHAT_ID")
    gcp_project_id: Optional[str] = Field(None, alias="GCP_PROJECT_ID")
    google_application_credentials: str = Field("", alias="GOOGLE_APPLICATION_CREDENTIALS")

class TachyonConfig(BaseModel):
    data_shards: int = Field(4, alias="TACHYON_DATA_SHARDS")
    parity_shards: int = Field(2, alias="TACHYON_PARITY_SHARDS")
    encryption_key: Optional[SecretStr] = Field(None, alias="TACHYON_ENCRYPTION_KEY")
    s3_api_key: Optional[SecretStr] = Field(None, alias="TACHYON_S3_API_KEY")

class VITConfig(BaseModel):
    app: AppConfig
    db: DatabaseConfig
    redis: RedisConfig
    ai: AIConfig
    blockchain: BlockchainConfig
    external: ExternalServicesConfig
    tachyon: TachyonConfig
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
