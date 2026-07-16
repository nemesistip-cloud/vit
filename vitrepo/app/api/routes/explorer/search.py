"""
Explorer Search API — Multi-entity lookup for the block explorer.
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.kernel import kernel

router = APIRouter(prefix="/search", tags=["Explorer Search"])

@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for blocks (height or hash), transactions (hash), or accounts (address).
    Delegates logic to the Blockchain Query Engine.
    """
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.query_engine:
        raise HTTPException(status_code=503, detail="Blockchain query engine unavailable")

    result = await subsystem.query_engine.unified_search(db, q)

    if result.get("type") == "not_found":
        raise HTTPException(status_code=404, detail=f"No matching blockchain entity found for '{q}'")

    return result
