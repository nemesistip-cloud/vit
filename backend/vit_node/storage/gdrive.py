import io
import os
import asyncio
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from app.core.errors import AppError
from vit_node.config import NODE_CONFIG_DIR

class PersonalDriveStorage:
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
    TOKEN_FILE = NODE_CONFIG_DIR / "gdrive_token.json"

    def __init__(self, client_secrets_path: str = None):
        self.client_secrets_path = client_secrets_path
        self.creds = None
        self._service = None

    def _get_credentials(self):
        if self.creds and self.creds.valid:
            return self.creds

        if self.TOKEN_FILE.exists():
            self.creds = Credentials.from_authorized_user_file(str(self.TOKEN_FILE), self.SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    # If refresh fails, we'll need to re-authenticate
                    pass

            if not self.creds or not self.creds.valid:
                return None # Need authentication

        return self.creds

    def authenticate(self) -> bool:
        from google_auth_oauthlib.flow import InstalledAppFlow
        if not self.client_secrets_path:
            raise AppError("Google Drive client secrets path not configured", code="gdrive_unconfigured")

        flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_path, self.SCOPES)
        self.creds = flow.run_local_server(port=0)

        NODE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.TOKEN_FILE, "w") as token:
            token.write(self.creds.to_json())

        return True

    @property
    def service(self):
        if self._service:
            return self._service

        creds = self._get_credentials()
        if not creds:
            raise AppError("Google Drive not authenticated", status_code=401, code="gdrive_unauthorized")

        self._service = build("drive", "v3", credentials=creds)
        return self._service

    def _get_or_create_folder(self, folder_name: str) -> str:
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = results.get('files', [])

        if files:
            return files[0]['id']

        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = self.service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

    async def store_shard(self, shard_id: str, data: bytes) -> str:
        return await asyncio.to_thread(self._store_shard_sync, shard_id, data)

    def _store_shard_sync(self, shard_id: str, data: bytes) -> str:
        folder_id = self._get_or_create_folder("VIT_Network_Node")

        file_metadata = {
            'name': shard_id,
            'parents': [folder_id]
        }

        media = MediaIoBaseUpload(io.BytesIO(data), mimetype='application/octet-stream')
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        return file.get('id')

    async def retrieve_shard(self, file_id: str) -> bytes:
        return await asyncio.to_thread(self._retrieve_shard_sync, file_id)

    def _retrieve_shard_sync(self, file_id: str) -> bytes:
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        return fh.getvalue()

    async def delete_shard(self, file_id: str) -> bool:
        return await asyncio.to_thread(self._delete_shard_sync, file_id)

    def _delete_shard_sync(self, file_id: str) -> bool:
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception:
            return False

    async def get_usage(self) -> dict:
        return await asyncio.to_thread(self._get_usage_sync)

    def _get_usage_sync(self) -> dict:
        about = self.service.about().get(fields="storageQuota").execute()
        quota = about.get("storageQuota", {})

        folder_id = self._get_or_create_folder("VIT_Network_Node")
        query = f"'{folder_id}' in parents and trashed = false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(size)').execute()
        files = results.get('files', [])

        node_usage = sum(int(f.get('size', 0)) for f in files)

        return {
            "used_bytes": int(quota.get("usage", 0)),
            "quota_bytes": int(quota.get("limit", 0)),
            "vit_node_folder_bytes": node_usage
        }
