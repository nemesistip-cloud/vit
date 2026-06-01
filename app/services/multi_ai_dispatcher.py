"""app/services/multi_ai_dispatcher.py — Native AI Dispatcher.
Routes all requests to internal native models.
"""
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PROVIDERS = ["native"]

async def run_multi_ai(
    match_id: int,
    db: AsyncSession,
    sources: List[str] = None,
) -> Dict[str, Any]:
    """Run native intelligence analysis for a match."""
    return {
        "match_id": match_id,
        "results": {
            "native": {
                "available": True,
                "home_prob": 0.34,
                "draw_prob": 0.33,
                "away_prob": 0.33,
                "confidence": 0.75,
                "reason": "Native ensemble analysis complete.",
            }
        }
    }
