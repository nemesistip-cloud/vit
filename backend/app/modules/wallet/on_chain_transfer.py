# app/modules/wallet/on_chain_transfer.py
"""API routes for on-chain VITCoin transfers and bridging."""

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.api.deps import get_current_user
from app.core.errors import AppError
from app.modules.wallet.chain_bridge import WalletChainBridge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wallet/bridge", tags=["Chain Bridge"])

class BridgeToChainRequest(BaseModel):
    amount: float = Field(..., gt=0)
    private_key: str = Field(..., description="Private key to sign the on-chain transfer")

class BridgeFromChainRequest(BaseModel):
    tx_hash: str

@router.post("/to-chain")
async def bridge_to_chain(
    request: BridgeToChainRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Move VIT from DB wallet to VIT Chain.
    """
    bridge = WalletChainBridge()
    tx_hash = await bridge.wallet_to_chain(
        db=db,
        user_id=current_user.id,
        amount=Decimal(str(request.amount)),
        private_key=request.private_key
    )

    return {
        "status": "submitted",
        "tx_hash": tx_hash,
        "amount": request.amount,
        "message": "VITCoin transfer to VIT Chain initiated."
    }

@router.post("/from-chain")
async def bridge_from_chain(
    request: BridgeFromChainRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync confirmed on-chain VIT back to DB wallet.
    """
    bridge = WalletChainBridge()
    success = await bridge.chain_to_wallet(
        db=db,
        user_id=current_user.id,
        tx_hash=request.tx_hash
    )

    if success:
        return {"status": "success", "message": "VITCoin successfully bridged back to DB wallet."}
    else:
        raise AppError("Failed to bridge from chain", status_code=500)
