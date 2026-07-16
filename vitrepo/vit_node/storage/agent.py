import base64
import hashlib
import json
import httpx
from datetime import datetime
from app.core.errors import AppError
from vit_node.storage.gdrive import PersonalDriveStorage
from vit_node.keystore import Keystore
from vit_node.config import NodeConfig

class StorageAgent:
    def __init__(self, drive: PersonalDriveStorage,
                 keystore: Keystore, config: NodeConfig):
        self.drive = drive
        self.keystore = keystore
        self.config = config
        self._shard_index = {} # shard_id -> file_id

    async def receive_shard_assignment(self, assignment: dict):
        """
        assignment: {shard_id, data_b64, manifest_id, shard_index, shard_hash}
        """
        shard_id = assignment.get("shard_id")
        data_b64 = assignment.get("data_b64")
        expected_hash = assignment.get("shard_hash")

        if not shard_id or not data_b64:
            raise AppError("Invalid shard assignment: missing data", code="invalid_assignment")

        # 1. Decode data from base64
        try:
            data = base64.b64decode(data_b64)
        except Exception:
            raise AppError("Failed to decode shard data", code="decode_error")

        # 2. Verify shard_hash matches sha256 of data
        if expected_hash:
            actual_hash = hashlib.sha256(data).hexdigest()
            if actual_hash != expected_hash:
                raise AppError("Shard data corruption detected (hash mismatch)", code="hash_mismatch")

        # 3. Store via drive.store_shard()
        file_id = await self.drive.store_shard(shard_id, data)
        self._shard_index[shard_id] = file_id

        # 4. Register with server: POST /api/tachyon/node/confirm_shard
        node_id = self.keystore.get_address()
        payload = {
            "node_id": node_id,
            "shard_id": shard_id,
            "file_id": file_id,
            "confirmed_at": datetime.utcnow().isoformat()
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config.api_url}/api/tachyon/node/confirm_shard",
                json=payload,
                timeout=30.0
            )
            if response.status_code != 200:
                raise AppError(f"Failed to confirm shard with server: {response.text}",
                             status_code=response.status_code, code="confirm_failed")

    async def get_assigned_shards(self) -> list[dict]:
        node_id = self.keystore.get_address()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.config.api_url}/api/tachyon/node/my_shards?node_id={node_id}",
                timeout=30.0
            )
            if response.status_code != 200:
                raise AppError(f"Failed to fetch assigned shards: {response.text}",
                             status_code=response.status_code, code="fetch_shards_failed")

            shards = response.json()
            # Update local index
            for shard in shards:
                if "shard_id" in shard and "file_id" in shard:
                    self._shard_index[shard["shard_id"]] = shard["file_id"]

            return shards

    async def serve_shard(self, shard_id: str) -> bytes | None:
        file_id = self._shard_index.get(shard_id)
        if not file_id:
            # Try to refresh assigned shards if not found locally
            await self.get_assigned_shards()
            file_id = self._shard_index.get(shard_id)

        if not file_id:
            return None

        try:
            return await self.drive.retrieve_shard(file_id)
        except Exception:
            return None
