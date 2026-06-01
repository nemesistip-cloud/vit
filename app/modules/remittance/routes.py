from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from .models import RemittanceTransaction
from app.api.deps import get_current_user
from app.db.models import User

router = APIRouter(prefix="/remittance", tags=["Remittance"])

@router.get("/history")
async def get_remittance_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RemittanceTransaction).where(RemittanceTransaction.user_id == user.id))
    return result.scalars().all()
