import os
from app.services.gcp_secrets import gcp_secrets
async def load_all_secrets():
    """Load secrets from Google Secret Manager if running in GCP."""
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GCS_PROJECT_ID")
    if project_id:
        secrets = [
            "STRIPE_SECRET_KEY",
            "STRIPE_WEBHOOK_SECRET",
            "PAYSTACK_SECRET_KEY",
            "PAYSTACK_WEBHOOK_SECRET",
            "JWT_SECRET_KEY",
            "SECRET_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "FOOTBALL_DATA_API_KEY",
            "ODDS_API_KEY",
            "ISPORTS_API_KEY",
            "TELEGRAM_BOT_TOKEN",
            "RESEND_API_KEY",
        ]
        await gcp_secrets.load_secrets_to_env(secrets)
