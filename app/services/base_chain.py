"""Base L2 (chain_id=8453) connection for VITCoin on-chain operations (Async)."""
import os
import logging
from typing import Optional
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.middleware import async_geth_poa_middleware

log = logging.getLogger(__name__)

BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
try:
    BASE_CHAIN_ID = int(os.getenv("BASE_CHAIN_ID", "8453"))
except (ValueError, TypeError):
    BASE_CHAIN_ID = 8453
VITCOIN_CONTRACT_ADDRESS = os.getenv("VIT_CONTRACT_ADDRESS", "")

_w3 = None

def get_w3() -> AsyncWeb3:
    """Returns a memoized AsyncWeb3 instance connected to Base L2."""
    global _w3
    if _w3 is None:
        _w3 = AsyncWeb3(AsyncHTTPProvider(BASE_RPC_URL))
        # inject POA middleware for compatibility with some L2 nodes
        _w3.middleware_onion.inject(async_geth_poa_middleware, layer=0)
    return _w3

async def is_connected() -> bool:
    """Checks if the Web3 provider is reachable (async)."""
    try:
        return await get_w3().is_connected()
    except Exception as e:
        log.warning(f"[base_chain] Connection check failed: {e}")
        return False

async def get_block_number() -> Optional[int]:
    """Returns the current block number from the chain (async)."""
    try:
        w3 = get_w3()
        if await w3.is_connected():
            return await w3.eth.block_number
        return None
    except Exception:
        return None

async def get_eth_balance(address: str) -> float:
    """Returns ETH balance in ether (not wei) (async)."""
    try:
        w3 = get_w3()
        if not w3.is_address(address):
            return 0.0
        bal_wei = await w3.eth.get_balance(w3.to_checksum_address(address))
        return float(w3.from_wei(bal_wei, 'ether'))
    except Exception as e:
        log.warning(f"[base_chain] Failed to get ETH balance for {address}: {e}")
        return 0.0

# ── VITCoin ERC-20 Support ──────────────────────────────────────────────────

VITCOIN_ABI = [
    {"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"to","type":"address"},{"name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"stateMutability":"view","type":"function"},
]

def get_vitcoin_contract():
    """Returns the VITCoin contract instance if the address is configured."""
    if not VITCOIN_CONTRACT_ADDRESS:
        return None
    try:
        w3 = get_w3()
        return w3.eth.contract(
            address=w3.to_checksum_address(VITCOIN_CONTRACT_ADDRESS),
            abi=VITCOIN_ABI
        )
    except Exception as e:
        log.error(f"[base_chain] Failed to initialize contract: {e}")
        return None

async def get_vitcoin_balance(wallet_address: str) -> float:
    """Returns VITCoin ERC-20 balance for the given wallet address (async)."""
    contract = get_vitcoin_contract()
    if not contract:
        return 0.0
    try:
        w3 = get_w3()
        if not w3.is_address(wallet_address):
            return 0.0
        # Contract calls are async in AsyncWeb3
        raw_bal = await contract.functions.balanceOf(w3.to_checksum_address(wallet_address)).call()
        decimals = await contract.functions.decimals().call()
        return float(raw_bal) / (10 ** decimals)
    except Exception as e:
        log.warning(f"[base_chain] Failed to get VIT balance for {wallet_address}: {e}")
        return 0.0

async def get_chain_status() -> dict:
    """Compatibility helper for the /chain-status route (async)."""
    w3 = get_w3()
    connected = await w3.is_connected()
    block = await w3.eth.block_number if connected else None

    chain_id = None
    if connected:
        try:
            chain_id = await w3.eth.chain_id
        except Exception:
            pass

    return {
        "connected": connected,
        "rpc_url": BASE_RPC_URL,
        "chain_id": chain_id or BASE_CHAIN_ID,
        "chain_id_ok": chain_id == BASE_CHAIN_ID if chain_id else False,
        "block_number": block,
        "contract_address": VITCOIN_CONTRACT_ADDRESS or None,
    }

async def get_token_balance(address: str) -> Optional[str]:
    """Compatibility helper for existing routes — returns hex string or None (async)."""
    contract = get_vitcoin_contract()
    if not contract:
        return None
    try:
        w3 = get_w3()
        raw_bal = await contract.functions.balanceOf(w3.to_checksum_address(address)).call()
        return hex(raw_bal)
    except Exception:
        return None
