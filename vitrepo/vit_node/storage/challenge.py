import hashlib
import httpx
import json
import asyncio
from datetime import datetime
from app.core.errors import AppError
from vit_node.storage.agent import StorageAgent
from vit_node.keystore import Keystore

class ChallengeResponder:
    def __init__(self, agent: StorageAgent, keystore: Keystore):
        self.agent = agent
        self.keystore = keystore

    async def respond_to_challenge(self, challenge: dict, password: str) -> bool:
        """
        challenge: {challenge_id, manifest_id, shard_id, shard_index, nonce, deadline}
        """
        challenge_id = challenge.get("challenge_id")
        shard_id = challenge.get("shard_id")
        nonce = challenge.get("nonce")
        deadline_str = challenge.get("deadline")

        if not challenge_id or not shard_id or not nonce:
            return False

        # 1. Check deadline not passed
        if deadline_str:
            deadline = datetime.fromisoformat(deadline_str)
            if datetime.utcnow() > deadline:
                return False

        # 2. Retrieve shard data from local drive
        shard_data = await self.agent.serve_shard(shard_id)
        if not shard_data:
            return False

        # 3. Compute response_hash = sha256(shard_data + nonce)
        hasher = hashlib.sha256()
        hasher.update(shard_data)
        hasher.update(nonce.encode())
        response_hash = hasher.hexdigest()

        # 4. Sign response_hash with keystore
        # Note: keystore.sign expects data as bytes and a password
        signature = self.keystore.sign(response_hash.encode(), password)
        node_id = self.keystore.get_address()

        # 5. POST to {api_url}/api/chain/consensus/respond
        payload = {
            "challenge_id": challenge_id,
            "response_hash": response_hash,
            "signature": signature,
            "node_id": node_id
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.agent.config.api_url}/api/chain/consensus/respond",
                    json=payload,
                    timeout=15.0
                )
                return response.status_code == 200
            except Exception:
                return False

    async def listen_for_challenges(self, ws_connection, password: str):
        """
        Handles incoming STORAGE_CHALLENGE messages from WebSocket gossip connection.
        """
        try:
            async for message in ws_connection:
                data = json.loads(message)
                if data.get("type") == "STORAGE_CHALLENGE":
                    challenge = data.get("payload")
                    if challenge:
                        # We run response in background to not block the socket
                        asyncio.create_task(self.respond_to_challenge(challenge, password))
        except Exception:
            # Socket closed or error
            pass
