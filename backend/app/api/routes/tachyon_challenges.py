"""
TRACK-008: Tachyon Storage Challenge REST API
Exposes challenge issuance, response verification, and scheduler stats.

Prefix: /api/tachyon/challenges
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tachyon/challenges", tags=["Tachyon Challenges"])


class ChallengeResponse(BaseModel):
    challenge_id: str
    digest: str


@router.get("/stats")
async def get_challenge_stats():
    """Return aggregate challenge statistics and scheduler state."""
    from tachyon.core.challenge import challenge_store, challenge_scheduler
    return {
        "scheduler": {
            "running": challenge_scheduler._running,
            "rounds_run": challenge_scheduler.rounds_run,
            "last_round_at": (
                challenge_scheduler.last_round_at.isoformat()
                if challenge_scheduler.last_round_at else None
            ),
            "interval_s": challenge_scheduler.interval_s,
        },
        "challenges": challenge_store.stats(),
    }


@router.get("/recent")
async def list_recent_challenges(limit: int = 50, _: Any = Depends(get_current_user)):
    """List recent challenge records (admin use)."""
    from tachyon.core.challenge import challenge_store
    return {"challenges": challenge_store.list_recent(limit=limit)}


@router.post("/respond")
async def respond_to_challenge(body: ChallengeResponse):
    """
    Node endpoint: submit a challenge response.
    Body: { challenge_id, digest }
    Returns 200 if passed, 400 if failed.
    """
    from tachyon.core.challenge import verify_challenge_response
    passed = verify_challenge_response(body.challenge_id, body.digest)
    if not passed:
        raise HTTPException(status_code=400, detail="Challenge response failed or invalid")
    return {"challenge_id": body.challenge_id, "status": "passed"}


@router.post("/trigger-round")
async def trigger_challenge_round(_: Any = Depends(get_current_user)):
    """Manually trigger a challenge round (admin/testing)."""
    from tachyon.core.challenge import challenge_scheduler
    import asyncio
    result = await asyncio.wait_for(challenge_scheduler.run_challenge_round(), timeout=60.0)
    return {"status": "completed", "stats": result}
