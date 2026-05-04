# app/services/base_chain.py
# G06: Base L2 chain connection code (without real ETH deploy).
# Provides chain-status checks and stub transaction helpers.
# Set BASE_RPC_URL env var (e.g. https://mainnet.base.org or a testnet URL).

from __future__ import annotations

import logging
import os
import time
from typing import Optional

log = logging.getLogger(__name__)

BASE_RPC_URL    = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
BASE_CHAIN_ID   = int(os.getenv("BASE_CHAIN_ID", "8453"))      # 84532 = Base Sepolia
CONTRACT_ADDR   = os.getenv("VIT_CONTRACT_ADDRESS", "")        # ERC-20 once deployed


# ── Lightweight JSON-RPC helper (no web3 dependency required) ─────────────────

async def _rpc(method: str, params: list) -> dict:
    import httpx
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(BASE_RPC_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


# ── Public helpers ────────────────────────────────────────────────────────────

async def get_chain_status() -> dict:
    """
    Returns basic chain health: block number, chain-id, latency.
    Safe to call even if RPC is unreachable — returns error details.
    """
    t0 = time.monotonic()
    try:
        block_resp   = await _rpc("eth_blockNumber", [])
        chainid_resp = await _rpc("eth_chainId",    [])
        latency_ms   = int((time.monotonic() - t0) * 1000)

        block_hex    = block_resp.get("result", "0x0")
        chain_hex    = chainid_resp.get("result", "0x0")
        block_number = int(block_hex, 16)
        chain_id     = int(chain_hex, 16)

        return {
            "connected":       True,
            "rpc_url":         BASE_RPC_URL,
            "chain_id":        chain_id,
            "chain_id_ok":     chain_id == BASE_CHAIN_ID,
            "block_number":    block_number,
            "latency_ms":      latency_ms,
            "contract_address": CONTRACT_ADDR or None,
        }
    except Exception as exc:
        log.warning("[base_chain] RPC unreachable: %s", exc)
        return {
            "connected":        False,
            "rpc_url":          BASE_RPC_URL,
            "chain_id":         BASE_CHAIN_ID,
            "chain_id_ok":      False,
            "block_number":     None,
            "latency_ms":       None,
            "contract_address": CONTRACT_ADDR or None,
            "error":            str(exc),
        }


async def get_token_balance(address: str) -> Optional[str]:
    """
    Returns VITCoin ERC-20 balance for address (hex string).
    Returns None if contract not deployed or RPC unreachable.
    """
    if not CONTRACT_ADDR:
        return None
    # balanceOf(address) selector = 0x70a08231
    padded = address.lower().replace("0x", "").zfill(64)
    data   = f"0x70a08231{padded}"
    try:
        result = await _rpc("eth_call", [{"to": CONTRACT_ADDR, "data": data}, "latest"])
        return result.get("result")
    except Exception as exc:
        log.warning("[base_chain] balanceOf error: %s", exc)
        return None


async def estimate_gas(from_addr: str, to_addr: str, data: str = "0x") -> Optional[int]:
    """Estimate gas for a transaction. Returns None on failure."""
    try:
        result = await _rpc("eth_estimateGas", [{"from": from_addr, "to": to_addr, "data": data}])
        return int(result["result"], 16)
    except Exception as exc:
        log.warning("[base_chain] estimateGas error: %s", exc)
        return None
