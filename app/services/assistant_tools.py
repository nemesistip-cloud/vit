"""app/services/assistant_tools.py — Tool definitions for the AI Assistant."""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.db.database import AsyncSessionLocal
from app.db.repositories import MatchRepository, AIPredictionRepository, CLVRepository
from app.agents.coordinator import get_coordinator
from app.services.odds_api import OddsAPIClient
from app.services.isports_api import ISportsClient, ISPORTS_LEAGUE_IDS

logger = logging.getLogger(__name__)

async def get_live_odds(league: str) -> Dict[str, Any]:
    """Fetch real-time market odds for a specific league from The Odds API."""
    api_key = os.getenv("THE_ODDS_API_KEY") or os.getenv("ODDS_API_KEY")
    if not api_key:
        return {"error": "Odds API key not configured."}

    client = OddsAPIClient(api_key)
    try:
        # Map common league names to Odds API keys if necessary
        sport_key = OddsAPIClient.SPORT_MAPPING.get(league.lower(), league)
        odds_list = await client.get_odds(sport=sport_key)

        if not odds_list:
            return {"message": f"No live odds found for {league}."}

        return {
            "league": league,
            "odds": [
                {
                    "home_team": o.home_team,
                    "away_team": o.away_team,
                    "bookmaker": o.bookmaker,
                    "home_odds": o.home_odds,
                    "draw_odds": o.draw_odds,
                    "away_odds": o.away_odds,
                    "timestamp": o.timestamp.isoformat() if o.timestamp else None
                }
                for o in odds_list[:15] # Limit to 15 matches to avoid blowing up context
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching live odds: {e}")
        return {"error": str(e)}
    finally:
        await client.close()

async def get_live_scores(league: Optional[str] = None) -> Dict[str, Any]:
    """Fetch current live scores for active matches from iSports API."""
    api_key = os.getenv("ISPORTS_API_KEY")
    if not api_key:
        return {"error": "iSports API key not configured."}

    client = ISportsClient(api_key)
    try:
        league_id = None
        if league:
            league_id = ISPORTS_LEAGUE_IDS.get(league.lower())

        scores = await client.get_livescores(league_id=league_id)
        if not scores:
            return {"message": "No live matches currently in progress."}

        formatted = []
        for s in scores[:20]:
            formatted.append(client.format_match_data(s, league or "Unknown"))

        return {
            "live_scores": formatted
        }
    except Exception as e:
        logger.error(f"Error fetching live scores: {e}")
        return {"error": str(e)}

async def get_external_fixtures(league: str) -> Dict[str, Any]:
    """Search for upcoming fixtures in external iSports API for a specific league."""
    api_key = os.getenv("ISPORTS_API_KEY")
    if not api_key:
        return {"error": "iSports API key not configured."}

    client = ISportsClient(api_key)
    try:
        league_id = ISPORTS_LEAGUE_IDS.get(league.lower())
        if not league_id:
            return {"error": f"League '{league}' not supported by iSports integration. Supported: {list(ISPORTS_LEAGUE_IDS.keys())}"}

        matches = await client.get_fixtures_and_results(league_id)
        if not matches:
            return {"message": f"No fixtures found for {league} in external API."}

        # Filter for upcoming only (status 0)
        upcoming = [m for m in matches if str(m.get("status")) == "0"]

        formatted = []
        for m in upcoming[:15]:
            formatted.append(client.format_match_data(m, league))

        return {
            "league": league,
            "upcoming_fixtures": formatted
        }
    except Exception as e:
        logger.error(f"Error fetching external fixtures: {e}")
        return {"error": str(e)}

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
                "name": "get_live_odds",
                "description": "Fetch real-time market odds for a specific league from The Odds API.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "league": {
                            "type": "STRING",
                            "description": "The league name (e.g., 'premier_league', 'la_liga')."
                        }
                    },
                    "required": ["league"]
                }
            },
            {
                "name": "get_live_scores",
                "description": "Fetch current live scores for active matches from iSports API.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "league": {
                            "type": "STRING",
                            "description": "Optional league name to filter live scores."
                        }
                    }
                }
            },
            {
                "name": "get_external_fixtures",
                "description": "Search for upcoming fixtures in external iSports API for a specific league.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "league": {
                            "type": "STRING",
                            "description": "The league name (e.g., 'premier_league', 'la_liga')."
                        }
                    },
                    "required": ["league"]
                }
            },
            {
                "name": "get_upcoming_matches",
                "description": "Fetch upcoming football matches from the platform's database.",
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
    "get_live_odds": get_live_odds,
    "get_live_scores": get_live_scores,
    "get_external_fixtures": get_external_fixtures,
    "get_upcoming_matches": get_upcoming_matches,
    "get_match_insights": get_match_insights,
    "get_system_health": get_system_health,
    "get_market_trends": get_market_trends,
}
