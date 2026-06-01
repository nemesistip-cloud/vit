import os, asyncio
from google.cloud import secretmanager
class GCPSecretsClient:
    def __init__(self): self.project_id = os.getenv("GCS_PROJECT_ID")
    async def load_secrets_to_env(self, names):
        if not self.project_id: return 0
        client = secretmanager.SecretManagerServiceClient()
        count = 0
        for name in names:
            try:
                res = client.access_secret_version(request={"name": f"projects/{self.project_id}/secrets/{name}/versions/latest"})
                os.environ[name] = res.payload.data.decode("UTF-8")
                count += 1
            except: pass
        return count
gcp_secrets = GCPSecretsClient()
