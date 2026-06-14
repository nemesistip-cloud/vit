"""app/api/routes/model_performance.py — Model accountability and accuracy tracking."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.modules.ai.models import ModelMetadata

router = APIRouter(prefix="/models", tags=["AI"])

@router.get("/performance")
async def get_model_performance(db: AsyncSession = Depends(get_db)):
    """Return live performance metrics for all ensemble models."""
    stmt = select(ModelMetadata).order_by(ModelMetadata.weight.desc())
    result = await db.execute(stmt)
    models = result.scalars().all()

    return {
        "status": "ok",
        "models": [
            {
                "key": m.key,
                "name": m.name,
                "weight": float(m.weight or 0),
                "accuracy": float(m.clv_score or 0) if hasattr(m, "clv_score") else 0,
                "samples": m.clv_samples if hasattr(m, "clv_samples") else 0
            }
            for m in models
        ]
    }
