from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from .models import PolicyImpact, PolicyScenario
from .services import PolicyService

router = APIRouter(prefix="/policy", tags=["Policy"])

@router.get("/impacts")
async def get_policy_impacts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PolicyImpact))
    return result.scalars().all()

@router.post("/simulate/{scenario_id}")
async def simulate_policy_scenario(scenario_id: int, db: AsyncSession = Depends(get_db)):
    prediction = await PolicyService.simulate_policy(db, scenario_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"status": "success", "prediction": prediction}
