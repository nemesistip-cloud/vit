import os
from app.services.gcp_secrets import gcp_secrets
async def load_all_secrets():
    if os.getenv("GCS_PROJECT_ID") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        await gcp_secrets.load_secrets_to_env(["STRIPE_SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL"])
