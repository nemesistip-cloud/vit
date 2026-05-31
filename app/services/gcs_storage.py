import os, asyncio
from google.cloud import storage
class GCSStorageClient:
    def __init__(self):
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        self.project_id = os.getenv("GCS_PROJECT_ID")
    async def upload_model(self, path, key): return await asyncio.to_thread(self._up, path, key)
    def _up(self, path, key):
        client = storage.Client(project=self.project_id)
        blob = client.bucket(self.bucket_name).blob(key)
        blob.upload_from_filename(path)
        return f"gs://{self.bucket_name}/{key}"
    async def download_model(self, key, path): return await asyncio.to_thread(self._dl, key, path)
    def _dl(self, key, path):
        client = storage.Client(project=self.project_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        client.bucket(self.bucket_name).blob(key).download_to_filename(path)
        return path
gcs_storage = GCSStorageClient()
