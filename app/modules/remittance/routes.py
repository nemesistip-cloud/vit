from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from .models import RemittanceTransaction
from app.api.deps import get_current_user
from app.db.models import User
from app.modules.wallet.services import WalletService, Currency
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional

router = APIRouter(prefix="/remittance", tags=["Remittance"])

class SendRemittanceRequest(BaseModel):
    recipient_address: str
    amount: float
    currency: str
    note: Optional[str] = None

class ReceiveRemittanceRequest(BaseModel):
    sender_address: str
    amount: float
    currency: str
    reference: str

@router.post("/send")
async def send_remittance(
    body: SendRemittanceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send remittance: check balance, debit wallet, create transaction."""
    wallet_service = WalletService(db)
    wallet = await wallet_service.get_or_create_wallet(current_user.id)

    try:
        currency_enum = Currency[body.currency.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unsupported currency: {body.currency}")

    balance = await wallet_service.get_balance(wallet.id, currency_enum)
    amount_dec = Decimal(str(body.amount))

    if balance < amount_dec:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance.")

    # Debit wallet
    await wallet_service.debit(
        wallet_id=wallet.id,
        user_id=current_user.id,
        currency=currency_enum,
        amount=amount_dec,
        tx_type="REMITTANCE_OUT",
        reference=f"REMIT:{body.recipient_address[:20]}",
        metadata={"note": body.note, "recipient": body.recipient_address}
    )

    # Create remittance record
    tx = RemittanceTransaction(
        user_id=current_user.id,
        amount=amount_dec,
        currency=body.currency.upper(),
        direction="outbound",
        status="pending",
        note=body.note,
        recipient_address=body.recipient_address
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    return {
        "transaction_id": tx.id,
        "status": tx.status,
        "estimated_arrival": "1-3 business days"
    }

@router.post("/receive")
async def receive_remittance(
    body: ReceiveRemittanceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Receive remittance: create transaction, credit wallet when confirmed."""
    amount_dec = Decimal(str(body.amount))

    # Create remittance record
    tx = RemittanceTransaction(
        user_id=current_user.id,
        amount=amount_dec,
        currency=body.currency.upper(),
        direction="inbound",
        status="pending",
        sender_address=body.sender_address,
        reference=body.reference
    )
    db.add(tx)
    await db.flush()
    await db.commit()
    await db.refresh(tx)

    return {
        "transaction_id": tx.id,
        "status": tx.status
    }

@router.get("/history")
async def get_remittance_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return actual RemittanceTransaction rows for the authenticated user."""
    result = await db.execute(
        select(RemittanceTransaction)
        .where(RemittanceTransaction.user_id == user.id)
        .order_by(desc(RemittanceTransaction.created_at))
        .limit(50)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "direction": r.direction,
            "amount": float(r.amount),
            "currency": r.currency,
            "status": r.status,
            "note": r.note,
            "reference": r.reference,
            "created_at": r.created_at.isoformat()
        }
        for r in rows
    ]
