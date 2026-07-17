import json
import time
import uuid
from decimal import Decimal
from typing import List, Optional, Any
from coincurve import PrivateKey
import hashlib

class WalletAPI:
    """
    API for VIT Wallet operations, including on-chain VIT Chain transfers.
    """
    def __init__(self, client):
        self.client = client

    async def get_balance(self, address: str) -> Decimal:
        """
        Returns on-chain VIT balance for the given address.
        """
        resp = await self.client.rpc_call("eth_getBalance", [address, "latest"])
        if resp.startswith("0x"):
            # Wei-equivalent hex string
            return Decimal(int(resp, 16)) / Decimal("1000000000000000000")
        return Decimal(resp)

    async def transfer(self, to_address: str, amount: Decimal, private_key: Optional[str] = None, idempotency_key: Optional[str] = None) -> str:
        """
        Sends VIT from the account associated with the private key.
        Amount is in VIT (will be converted to Wei for transmission).
        """
        priv_key_hex = private_key or self.client.private_key
        if not priv_key_hex:
            raise ValueError("Private key is required for transfers")

        priv = PrivateKey.from_hex(priv_key_hex)
        # Derive address
        from .chain import ChainAPI
        from_address = ChainAPI.public_key_to_address(priv.public_key.format(compressed=False).hex())

        # Get nonce
        nonce_hex = await self.client.rpc_call("eth_getTransactionCount", [from_address, "latest"])
        nonce = int(nonce_hex, 16)

        # Construct Transaction
        timestamp = int(time.time())
        gas_fee = Decimal("0.001")

        # VIT Chain RPC expects amount in VIT as string for JSON-RPC handlers.py
        # but internal vit_chain/core/transaction.py handles it as Decimal.
        # handlers.py uses Decimal(tx_data["amount"])

        payload = {
            "from_address": from_address,
            "to_address": to_address,
            "amount": str(amount),
            "nonce": nonce,
            "gas_fee": str(gas_fee),
            "data": None,
            "timestamp": timestamp
        }

        # Compute Hash (must match vit_chain/core/transaction.py)
        canonical_json = json.dumps(payload, sort_keys=True)
        tx_hash = ChainAPI.keccak256(canonical_json.encode("utf-8"))

        # Sign (Recoverable)
        signature = priv.sign_recoverable(bytes.fromhex(tx_hash)).hex()

        # Build final tx payload for eth_sendRawTransaction
        tx_data = payload.copy()
        tx_data["signature"] = signature
        tx_data["tx_hash"] = tx_hash

        raw_tx_hex = json.dumps(tx_data).encode("utf-8").hex()

        headers = {}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        elif not idempotency_key:
             headers["X-Idempotency-Key"] = str(uuid.uuid4())

        # NOTE: rpc_call helper needs to support headers if we want idempotency on RPC
        # For now we'll call client.request directly
        rpc_payload = {
            "jsonrpc": "2.0",
            "method": "eth_sendRawTransaction",
            "params": [raw_tx_hex],
            "id": 1
        }
        resp = await self.client.request("POST", "/api/chain/rpc", json=rpc_payload, headers=headers)

        if isinstance(resp, dict) and "error" in resp:
            from .exceptions import VITRPCError
            raise VITRPCError(f"RPC Error: {resp['error']}")

        return resp.get("result")

    async def get_transactions(self, address: str, limit: int = 20) -> List[dict]:
        """
        Returns recent transactions for the given address.
        Note: Currently calls the custodial history API.
        """
        # Note: address is ignored in the current custodial /api/wallet/transactions endpoint
        # which returns history for the authenticated user (via api_key).
        resp = await self.client.request("GET", "/api/wallet/transactions", params={"limit": limit})
        return resp.get("transactions", [])
