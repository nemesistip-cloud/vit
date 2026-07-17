from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.db.database import get_db
from app.services.results_settler import settle_results

router = APIRouter(prefix="/sports/webhooks", tags=["sports-webhooks"])
logger = logging.getLogger(__name__)

@router.post("/isports")
async def isports_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives match result updates from iSports via webhook.
    Triggers the settlement pipeline.
    """
    payload = await request.json()
    logger.info(f"Received iSports webhook: {payload}")

    # In a real implementation, we would verify the signature/source
    # and possibly filter to only settle the specific match in the payload.
    # For now, we trigger a broad settlement pass for the last 2 days.

    result = await settle_results(days_back=2)
    return {"status": "success", "processed": result}

@router.post("/api-football")
async def api_football_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives match result updates from API-Football via webhook.
    """
    payload = await request.json()
    logger.info(f"Received API-Football webhook: {payload}")

    result = await settle_results(days_back=2)
    return {"status": "success", "processed": result}
