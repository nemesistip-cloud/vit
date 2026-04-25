"""Admin CLV utilities — manual backfill of missing closing-line values (v4.6.1)."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user
from app.services.clv_backfill import backfill_missing_clv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/clv", tags=["admin-clv"])


async def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


@router.post("/backfill")
async def trigger_clv_backfill(
    limit: int = Query(500, ge=1, le=5000),
    dry_run: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_admin),
):
    """
    Manually rebuild CLV entries for settled predictions whose closing
    line value was never populated. Hooks into the same routine the
    background loop runs hourly. `dry_run=true` returns a preview count
    without writing.
    """
    try:
        counts = await backfill_missing_clv(db, limit=limit, dry_run=dry_run)
    except Exception as e:
        logger.exception("CLV backfill failed")
        raise HTTPException(status_code=500, detail=f"backfill_failed: {e}")
    return {"ok": True, "dry_run": dry_run, **counts}
