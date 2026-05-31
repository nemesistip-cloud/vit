from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.trust.engine import get_user_trust_score
from app.modules.merit.service import get_or_create_merit_score
from app.modules.identity.engine import get_or_create_system_id
from app.db.models import User

@dataclass
class VITPassport:
    user_id: int
    system_id: str
    trust_score: float
    merit_score: float
    merit_tier: str
    is_kyc_verified: bool
    badges: Dict[str, bool]

class PassportService:
    @staticmethod
    async def get_passport(db: AsyncSession, user_id: int) -> VITPassport:
        user = await db.get(User, user_id)
        if not user: raise ValueError("User not found")
        trust_score = await get_user_trust_score(db, user_id)
        ms = await get_or_create_merit_score(db, user_id)
        sys_id = await get_or_create_system_id(user_id, user, db)
        return VITPassport(
            user_id=user_id, system_id=sys_id.sid, trust_score=float(trust_score),
            merit_score=float(ms.score), merit_tier=ms.tier.value,
            is_kyc_verified=(user.kyc_status == "approved"), badges=sys_id.badges or {}
        )
