from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.rewards.service import RewardService

router = APIRouter(prefix="/api/postback", tags=["postback"])


@router.post("/{provider}")
async def receive_postback(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive a provider postback and issue the corresponding reward."""
    body = await request.body()
    headers = dict(request.headers)
    client_host = request.client.host if request.client else None

    try:
        event = await RewardService.process_postback(
            db=db,
            provider=provider,
            body=body,
            headers=headers,
            ip_address=client_host,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return {
        "success": True,
        "provider": provider,
        "event_id": event.id,
        "status": event.status,
        "wallet_tx_id": event.wallet_tx_id,
        "amount": float(event.amount),
        "currency": event.currency,
    }
