"""
multichain.py — Multi-chain routing in the VIT gateway (Phase IV)

Provides a unified routing layer that selects the correct chain/network
for a given transaction type, asset, or destination address. Supports
VIT native chain, Base (L2), and stub entries for future integrations.
"""

from __future__ import annotations

import time
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/chain", tags=["multichain"])


# ── Chain registry ─────────────────────────────────────────────────────────────

SUPPORTED_CHAINS: List[dict] = [
    {
        "id": "vit-native",
        "name": "VIT Native Chain",
        "type": "l1",
        "currency": "VIT",
        "rpc_endpoint": "/api/chain/rpc",
        "explorer": "/chain",
        "status": "active",
        "finality_blocks": 1,
        "avg_block_time_ms": 3000,
    },
    {
        "id": "base-mainnet",
        "name": "Base (Coinbase L2)",
        "type": "l2",
        "currency": "ETH",
        "rpc_endpoint": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
        "status": "active",
        "finality_blocks": 12,
        "avg_block_time_ms": 2000,
    },
    {
        "id": "ethereum-mainnet",
        "name": "Ethereum Mainnet",
        "type": "l1",
        "currency": "ETH",
        "rpc_endpoint": "https://eth.llamarpc.com",
        "explorer": "https://etherscan.io",
        "status": "planned",
        "finality_blocks": 64,
        "avg_block_time_ms": 12000,
    },
    {
        "id": "solana-mainnet",
        "name": "Solana Mainnet",
        "type": "l1",
        "currency": "SOL",
        "rpc_endpoint": "https://api.mainnet-beta.solana.com",
        "explorer": "https://explorer.solana.com",
        "status": "planned",
        "finality_blocks": 32,
        "avg_block_time_ms": 400,
    },
]

# Routing rules: asset → preferred chain id
ASSET_ROUTING: dict = {
    "VIT": "vit-native",
    "ETH": "base-mainnet",
    "USDC": "base-mainnet",
    "USDT": "base-mainnet",
    "SOL": "solana-mainnet",
}

# Transaction type → preferred chain id
TX_TYPE_ROUTING: dict = {
    "prediction_attestation": "vit-native",
    "reward_payout": "vit-native",
    "governance_vote": "vit-native",
    "staking": "vit-native",
    "bridge": "base-mainnet",
    "nft_mint": "base-mainnet",
}


# ── Schemas ────────────────────────────────────────────────────────────────────

class RouteRequest(BaseModel):
    asset: Optional[str]   = Field(None, description="Asset symbol, e.g. VIT, ETH, USDC")
    tx_type: Optional[str] = Field(None, description="Transaction type key")
    destination: Optional[str] = Field(None, description="Destination address (used for chain detection)")
    amount: Optional[float] = Field(None, ge=0)


class RouteResult(BaseModel):
    chain_id: str
    chain_name: str
    rpc_endpoint: str
    explorer: str
    status: str
    estimated_fee_usd: float
    reasoning: str
    timestamp: int


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/networks", summary="List all supported chains")
async def list_networks():
    """Returns the full list of chains supported by the VIT gateway."""
    return {
        "networks": SUPPORTED_CHAINS,
        "default": "vit-native",
        "total": len(SUPPORTED_CHAINS),
    }


@router.get("/networks/{chain_id}", summary="Get chain details")
async def get_network(chain_id: str):
    chain = next((c for c in SUPPORTED_CHAINS if c["id"] == chain_id), None)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Chain '{chain_id}' not found")
    return chain


@router.post("/route", response_model=RouteResult, summary="Route a transaction to the optimal chain")
async def route_transaction(
    body: RouteRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Multi-chain routing oracle.

    Given an asset, transaction type, or destination address, selects the
    optimal chain and returns RPC endpoint, explorer URL, and fee estimate.
    Priority: tx_type > asset > default (vit-native).
    """
    chain_id = "vit-native"
    reasoning = "Default: VIT Native Chain"

    if body.tx_type and body.tx_type in TX_TYPE_ROUTING:
        chain_id = TX_TYPE_ROUTING[body.tx_type]
        reasoning = f"Routed by transaction type '{body.tx_type}'"
    elif body.asset and body.asset.upper() in ASSET_ROUTING:
        chain_id = ASSET_ROUTING[body.asset.upper()]
        reasoning = f"Routed by asset '{body.asset.upper()}'"

    chain = next((c for c in SUPPORTED_CHAINS if c["id"] == chain_id), SUPPORTED_CHAINS[0])

    # Simple fee estimation (mock — real integration would query gas oracle)
    base_fees: dict = {
        "vit-native":        0.001,
        "base-mainnet":      0.05,
        "ethereum-mainnet":  2.50,
        "solana-mainnet":    0.0005,
    }
    fee = base_fees.get(chain_id, 0.01)

    return RouteResult(
        chain_id=chain["id"],
        chain_name=chain["name"],
        rpc_endpoint=chain["rpc_endpoint"],
        explorer=chain["explorer"],
        status=chain["status"],
        estimated_fee_usd=fee,
        reasoning=reasoning,
        timestamp=int(time.time()),
    )
