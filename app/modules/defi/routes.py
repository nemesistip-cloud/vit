# app/modules/defi/routes.py
"""
DeFi Yield & Liquidity Pools — Phase VIII
Endpoints: browse pools, stake/unstake VIT, claim yield, LP positions,
           protocol stats and APY snapshots.
Balances are tracked in-memory and reconciled with the wallet module;
a full on-chain settlement via vit-contracts is the Phase IX upgrade path.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/defi", tags=["DeFi"])

# ── In-memory state ──────────────────────────────────────────────────────────
_POOLS: List[dict] = [
    {
        "id":          "vit-usdc-lp",
        "name":        "VIT / USDC",
        "token_a":     "VIT",
        "token_b":     "USDC",
        "tvl_usd":     2_450_000.0,
        "apy":         18.4,
        "volume_24h":  312_000.0,
        "fee_tier":    0.3,
        "protocol":    "VITSwap v2",
        "category":    "liquidity",
        "risk":        "medium",
        "created_at":  time.time(),
    },
    {
        "id":          "vit-eth-lp",
        "name":        "VIT / ETH",
        "token_a":     "VIT",
        "token_b":     "ETH",
        "tvl_usd":     1_820_000.0,
        "apy":         24.1,
        "volume_24h":  185_000.0,
        "fee_tier":    0.3,
        "protocol":    "VITSwap v2",
        "category":    "liquidity",
        "risk":        "high",
        "created_at":  time.time(),
    },
    {
        "id":          "vit-staking-flex",
        "name":        "VIT Flex Staking",
        "token_a":     "VIT",
        "token_b":     None,
        "tvl_usd":     5_100_000.0,
        "apy":         12.0,
        "volume_24h":  0.0,
        "fee_tier":    0.0,
        "protocol":    "VIT Staking Protocol",
        "category":    "staking",
        "risk":        "low",
        "created_at":  time.time(),
    },
    {
        "id":          "vit-staking-90d",
        "name":        "VIT 90-Day Lock",
        "token_a":     "VIT",
        "token_b":     None,
        "tvl_usd":     3_200_000.0,
        "apy":         32.5,
        "volume_24h":  0.0,
        "fee_tier":    0.0,
        "protocol":    "VIT Staking Protocol",
        "category":    "staking",
        "risk":        "low",
        "lock_days":   90,
        "created_at":  time.time(),
    },
    {
        "id":          "prediction-yield-vault",
        "name":        "Prediction Yield Vault",
        "token_a":     "VIT",
        "token_b":     None,
        "tvl_usd":     980_000.0,
        "apy":         41.8,
        "volume_24h":  0.0,
        "fee_tier":    0.0,
        "protocol":    "VIT Vault v1",
        "category":    "yield",
        "risk":        "high",
        "created_at":  time.time(),
    },
]

# user_id → [ {position} ]
_positions: Dict[int, List[dict]] = {}


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class StakeRequest(BaseModel):
    pool_id:   str
    amount:    float = Field(..., gt=0, description="Amount of token_a to deposit")
    lock_days: int   = Field(default=0, ge=0, le=365)


class UnstakeRequest(BaseModel):
    position_id: str


class ClaimRequest(BaseModel):
    position_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_pool(pool_id: str) -> dict:
    for p in _POOLS:
        if p["id"] == pool_id:
            return p
    raise HTTPException(404, f"Pool '{pool_id}' not found")


def _accrue_yield(pos: dict) -> float:
    """Estimate accrued yield since last claim."""
    elapsed_years = (time.time() - pos["last_claim_at"]) / (365.25 * 86400)
    return round(pos["amount"] * (pos["apy"] / 100) * elapsed_years, 6)


# ── Pools ─────────────────────────────────────────────────────────────────────

@router.get("/pools", summary="Browse all liquidity/staking pools")
async def list_pools(
    category: Optional[str] = Query(None, description="filter: liquidity | staking | yield"),
    sort_by:  str           = Query("tvl_usd", description="tvl_usd | apy | volume_24h"),
):
    pools = list(_POOLS)
    if category:
        pools = [p for p in pools if p.get("category") == category]
    if sort_by in {"tvl_usd", "apy", "volume_24h"}:
        pools.sort(key=lambda p: p.get(sort_by, 0), reverse=True)
    return {"pools": pools, "total": len(pools)}


@router.get("/pools/{pool_id}", summary="Get pool details")
async def get_pool(pool_id: str):
    return _get_pool(pool_id)


# ── Staking / LP deposit ──────────────────────────────────────────────────────

@router.post("/stake", summary="Stake tokens into a pool")
async def stake(body: StakeRequest, me: User = Depends(get_current_user)):
    pool = _get_pool(body.pool_id)
    pos = {
        "id":             str(uuid.uuid4()),
        "user_id":        me.id,
        "pool_id":        body.pool_id,
        "pool_name":      pool["name"],
        "amount":         body.amount,
        "token":          pool["token_a"],
        "apy":            pool["apy"],
        "lock_days":      body.lock_days or pool.get("lock_days", 0),
        "locked_until":   time.time() + body.lock_days * 86400 if body.lock_days else None,
        "staked_at":      time.time(),
        "last_claim_at":  time.time(),
        "status":         "active",
        "accrued_yield":  0.0,
    }
    _positions.setdefault(me.id, []).append(pos)
    # Update pool TVL (simulated)
    pool["tvl_usd"] += body.amount * 1.0  # 1 VIT ≈ $1 for demo
    logger.info("defi:stake user=%s pool=%s amount=%s", me.id, body.pool_id, body.amount)
    return {"ok": True, "position": pos}


@router.get("/positions", summary="My active DeFi positions")
async def get_positions(me: User = Depends(get_current_user)):
    positions = _positions.get(me.id, [])
    enriched = []
    for pos in positions:
        accrued = _accrue_yield(pos)
        enriched.append({**pos, "accrued_yield": accrued})
    return {"positions": enriched, "total": len(enriched)}


@router.post("/unstake", summary="Withdraw from a position")
async def unstake(body: UnstakeRequest, me: User = Depends(get_current_user)):
    positions = _positions.get(me.id, [])
    pos = next((p for p in positions if p["id"] == body.position_id), None)
    if not pos:
        raise HTTPException(404, "Position not found")
    if pos["locked_until"] and time.time() < pos["locked_until"]:
        remaining = int(pos["locked_until"] - time.time())
        raise HTTPException(400, f"Position locked for {remaining // 3600}h {(remaining % 3600) // 60}m")
    accrued = _accrue_yield(pos)
    pos["status"] = "closed"
    _positions[me.id] = [p for p in positions if p["id"] != body.position_id]
    logger.info("defi:unstake user=%s pos=%s yield=%.4f", me.id, body.position_id, accrued)
    return {"ok": True, "returned_amount": pos["amount"], "yield_claimed": accrued}


@router.post("/claim", summary="Claim accrued yield without unstaking")
async def claim_yield(body: ClaimRequest, me: User = Depends(get_current_user)):
    positions = _positions.get(me.id, [])
    pos = next((p for p in positions if p["id"] == body.position_id and p["status"] == "active"), None)
    if not pos:
        raise HTTPException(404, "Active position not found")
    accrued = _accrue_yield(pos)
    if accrued < 0.000001:
        raise HTTPException(400, "Accrued yield too small to claim")
    pos["last_claim_at"] = time.time()
    pos["accrued_yield"] = 0.0
    logger.info("defi:claim user=%s yield=%.6f", me.id, accrued)
    return {"ok": True, "claimed": accrued, "token": "VIT"}


# ── Protocol stats ────────────────────────────────────────────────────────────

@router.get("/stats", summary="Protocol-wide DeFi stats")
async def defi_stats():
    total_tvl    = sum(p["tvl_usd"]    for p in _POOLS)
    total_volume = sum(p["volume_24h"] for p in _POOLS)
    avg_apy      = sum(p["apy"]        for p in _POOLS) / len(_POOLS) if _POOLS else 0
    total_positions = sum(len(v) for v in _positions.values())
    return {
        "total_tvl_usd":       round(total_tvl,    2),
        "total_volume_24h":    round(total_volume, 2),
        "average_apy":         round(avg_apy,      2),
        "active_pools":        len(_POOLS),
        "active_positions":    total_positions,
    }


@router.get("/apy-history/{pool_id}", summary="APY snapshot history")
async def apy_history(pool_id: str):
    pool = _get_pool(pool_id)
    base = pool["apy"]
    # Synthetic 30-day history
    history = [
        {"date": f"D-{30 - i}", "apy": round(base * (0.92 + 0.08 * (i / 30)), 2)}
        for i in range(31)
    ]
    return {"pool_id": pool_id, "history": history}
