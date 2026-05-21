"""app/services/assistant_tools.py — Tool definitions for the AI Assistant."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.db.database import AsyncSessionLocal
from app.db.repositories import MatchRepository, AIPredictionRepository, CLVRepository
from app.agents.coordinator import get_coordinator

logger = logging.getLogger(__name__)

async def get_upcoming_matches(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch upcoming football matches from the platform."""
    async with AsyncSessionLocal() as db:
        repo = MatchRepository(db)
        matches = await repo.get_upcoming(limit=limit)
        return [
            {
                "id": m.id,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "league": m.league,
                "kickoff_time": m.kickoff_time.isoformat() if m.kickoff_time else None,
                "status": m.status,
            }
            for m in matches
        ]

async def get_match_insights(match_id: int) -> Dict[str, Any]:
    """Fetch deep AI insights and predictions for a specific match ID."""
    async with AsyncSessionLocal() as db:
        match_repo = MatchRepository(db)
        pred_repo = AIPredictionRepository(db)

        match = await match_repo.get_by_id(match_id)
        if not match:
            return {"error": f"Match with ID {match_id} not found."}

        predictions = await pred_repo.get_by_match(match_id)

        return {
            "match": {
                "home_team": match.home_team,
                "away_team": match.away_team,
                "league": match.league,
                "kickoff_time": match.kickoff_time.isoformat() if match.kickoff_time else None,
            },
            "predictions": [
                {
                    "source": p.source,
                    "home_prob": p.home_prob,
                    "draw_prob": p.draw_prob,
                    "away_prob": p.away_prob,
                    "confidence": p.confidence,
                    "was_correct": p.was_correct,
                }
                for p in predictions
            ]
        }

async def get_system_health() -> Dict[str, Any]:
    """Fetch the current status and performance of all autonomous agents in the VIT network."""
    try:
        coordinator = get_coordinator()
        return coordinator.summary()
    except Exception as e:
        logger.error(f"Error fetching system health: {e}")
        return {"error": "Could not fetch agent status."}

async def get_market_trends() -> Dict[str, Any]:
    """Fetch overall market trends and CLV (Closing Line Value) performance statistics."""
    async with AsyncSessionLocal() as db:
        repo = CLVRepository(db)
        return await repo.get_stats()

# Tool declarations for Gemini
GEMINI_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "get_upcoming_matches",
                "description": "Fetch upcoming football matches from the platform.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "limit": {
                            "type": "INTEGER",
                            "description": "Maximum number of matches to return (default 10)."
                        }
                    }
                }
            },
            {
                "name": "get_match_insights",
                "description": "Fetch deep AI insights and predictions for a specific match ID.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "match_id": {
                            "type": "INTEGER",
                            "description": "The unique ID of the match."
                        }
                    },
                    "required": ["match_id"]
                }
            },
            {
                "name": "get_system_health",
                "description": "Fetch the current status and performance of all autonomous agents in the VIT network.",
            },
            {
                "name": "get_market_trends",
                "description": "Fetch overall market trends and CLV (Closing Line Value) performance statistics.",
            }
        ]
    }
]

# Mapping tool names to functions
TOOL_MAP = {
    "get_upcoming_matches": get_upcoming_matches,
    "get_match_insights": get_match_insights,
    "get_system_health": get_system_health,
    "get_market_trends": get_market_trends,
}
