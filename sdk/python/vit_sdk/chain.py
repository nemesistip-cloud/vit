from decimal import Decimal
from typing import Dict, Any, Optional
import hashlib
from .exceptions import VITSDKError

class ChainAPI:
    """
    API for interacting with the VIT Chain (L2) and blockchain economy.
    """
    def __init__(self, client):
        self.client = client

    async def get_block(self, height_or_hash: Any) -> dict:
        """
        Returns block information by number (hex string or int) or hash.
        """
        if isinstance(height_or_hash, str) and height_or_hash.startswith("0x") and len(height_or_hash) == 66:
            # Looks like a 32-byte hash
            return await self.client.rpc_call("eth_getBlockByHash", [height_or_hash, True])

        if isinstance(height_or_hash, int):
            height_or_hash = hex(height_or_hash)
        elif height_or_hash != "latest" and not height_or_hash.startswith("0x"):
            # Assume it's a decimal number string
            height_or_hash = hex(int(height_or_hash))

        return await self.client.rpc_call("eth_getBlockByNumber", [height_or_hash, True])

    async def get_transaction(self, tx_hash: str) -> dict:
        """
        Returns transaction information for the given hash.
        """
        return await self.client.rpc_call("eth_getTransactionByHash", [tx_hash])

    async def get_balance(self, address: str) -> Decimal:
        """
        Returns on-chain VIT balance for the given address.
        """
        from .wallet import WalletAPI
        wallet = WalletAPI(self.client)
        return await wallet.get_balance(address)

    async def send_transaction(self, from_key: str, to_address: str, amount: Decimal) -> str:
        """
        Signs and sends an on-chain transaction.
        """
        from .wallet import WalletAPI
        wallet = WalletAPI(self.client)
        return await wallet.transfer(to_address, amount, private_key=from_key)

    async def get_chain_stats(self) -> dict:
        """
        Returns global blockchain and tokenomics metrics.
        """
        return await self.client.request("GET", "/api/blockchain/economy")

    @staticmethod
    def keccak256(data: bytes) -> str:
        """
        Keccak-256 implementation using eth-hash.
        """
        try:
            from eth_hash.auto import keccak
            return keccak(data).hex()
        except ImportError:
            raise VITSDKError("eth-hash package is required for Keccak-256 operations. Install it with pip install eth-hash[pycryptodome]")

    @staticmethod
    def public_key_to_address(public_key_hex: str) -> str:
        """
        Converts secp256k1 uncompressed public key to VIT address.
        Mirroring vit_chain/crypto/address.py.
        """
        if public_key_hex.startswith("0x"):
            public_key_hex = public_key_hex[2:]

        pub_bytes = bytes.fromhex(public_key_hex)
        if pub_bytes[0] == 0x04:
            pub_bytes = pub_bytes[1:]

        k_hash = ChainAPI.keccak256(pub_bytes)
        address_part = k_hash[-40:]
        return f"VIT{address_part}"
