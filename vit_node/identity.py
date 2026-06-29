import httpx
import json
from vit_node.keystore import Keystore
from vit_node.config import NodeConfig
from app.core.errors import AppError

try:
    # TODO: Import from vit_chain.crypto.ecdsa when 1.1 merges
    from vit_chain.crypto.ecdsa import PrivateKey
except ImportError:
    # Stub for pre-merge 1.1
    class PrivateKey:
        @classmethod
        def from_hex(cls, hex_str): return cls()
        @property
        def public_key(self):
            class PubKey:
                def format(self, **kwargs): return b"\x00"*65
            return PubKey()

class NodeIdentity:
    def __init__(self, keystore: Keystore, config: NodeConfig):
        self.keystore = keystore
        self.config = config

    async def register(self, password: str,
                        node_type: str = "storage",
                        capabilities: dict = None) -> dict:
        # 1. Get VIT address and private key
        private_key_hex, address = self.keystore.load(password)

        # 2. Get public key for registration
        # TODO: Stub crypto calls until 1.1 merges
        priv = PrivateKey.from_hex(private_key_hex)
        public_key_hex = priv.public_key.format(compressed=False).hex()

        # 3. Build registration payload
        payload = {
            "node_id": address,
            "public_key": public_key_hex,
            "node_type": node_type,
            "capabilities": capabilities or {},
            "ws_url": "direct"  # updated after P2P
        }

        # 4. Sign payload
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = self.keystore.sign(payload_bytes, password)

        # 5. POST to {api_url}/api/chain/peers/register
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_url}/api/chain/peers/register",
                    json={
                        "payload": payload,
                        "signature": signature
                    },
                    timeout=30.0
                )

                if response.status_code != 200:
                    raise AppError(f"Registration failed: {response.text}", status_code=response.status_code, code="registration_failed")

                result = response.json()

                # 6. Store registration result in config
                self.config.registration_result = result
                self.config.save()

                return result
        except httpx.RequestError as e:
            raise AppError(f"Network error during registration: {str(e)}", code="registration_network_error")
        except Exception as e:
            if isinstance(e, AppError):
                raise e
            raise AppError(f"Unexpected error during registration: {str(e)}", code="registration_unexpected_error")

    async def check_status(self) -> dict:
        node_id = self.keystore.get_address()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_url}/api/chain/peers/{node_id}",
                    timeout=30.0
                )

                if response.status_code != 200:
                    raise AppError(f"Status check failed: {response.text}", status_code=response.status_code, code="status_check_failed")

                return response.json()
        except httpx.RequestError as e:
            raise AppError(f"Network error during status check: {str(e)}", code="status_network_error")
        except Exception as e:
            if isinstance(e, AppError):
                raise e
            raise AppError(f"Unexpected error during status check: {str(e)}", code="status_unexpected_error")
