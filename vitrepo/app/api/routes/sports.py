from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from app.db.database import get_db
from app.db.models import Match, Team
from app.modules.sports.models import MarketMapping
from app.services.isports_api import ISportsClient, ISPORTS_LEAGUE_IDS
from app.services.football_api import FootballDataClient
from app.services.odds_api import OddsAPIClient
import os
from datetime import datetime

router = APIRouter(prefix="/sports", tags=["sports-infra"])
logger = logging.getLogger(__name__)

@router.post("/sync/fixtures")
async def sync_sports_fixtures(
    provider: str = Query("isports", description="Provider to sync from: isports, footballdata"),
    league_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Synchronizes fixtures from external sports providers.
    """
    if provider == "isports":
        isports_key = os.getenv("ISPORTS_API_KEY")
        if not isports_key:
            raise HTTPException(status_code=500, detail="ISPORTS_API_KEY not configured")

        client = ISportsClient(isports_key)
        leagues_to_sync = {name: lid for name, lid in ISPORTS_LEAGUE_IDS.items()}
        if league_id:
            # Filter to specific league if provided
            leagues_to_sync = {k: v for k, v in leagues_to_sync.items() if v == league_id}

        total_synced = 0
        for name, lid in leagues_to_sync.items():
            try:
                raw_matches = await client.get_fixtures_and_results(lid)
                for m in raw_matches:
                    # Status 0 is 'Not Started'
                    if str(m.get("status")) == "0":
                        formatted = client.format_match_data(m, name)
                        # Check if exists
                        ext_id = str(m.get("matchId"))
                        stmt = select(Match).where(Match.external_id == ext_id)
                        existing = (await db.execute(stmt)).scalar_one_or_none()

                        if not existing:
                            from datetime import datetime
                            kickoff = datetime.fromtimestamp(m.get("matchTime"), tz=None) if m.get("matchTime") else None
                            new_match = Match(
                                external_id=ext_id,
                                home_team=formatted["home_team"],
                                away_team=formatted["away_team"],
                                league=formatted["league"],
                                kickoff_time=kickoff,
                                status="scheduled",
                                source="isports",
                                sport="football"
                            )
                            db.add(new_match)
                            total_synced += 1
                await db.commit()
            except Exception as e:
                logger.error(f"Failed syncing league {name}: {e}")
                await db.rollback()

        return {"status": "success", "synced": total_synced, "provider": "isports"}

    elif provider == "footballdata":
        fd_key = os.getenv("FOOTBALL_DATA_API_KEY")
        if not fd_key:
            raise HTTPException(status_code=500, detail="FOOTBALL_DATA_API_KEY not configured")

        client = FootballDataClient(fd_key)
        # For simplicity, sync major leagues
        competitions = ["premier_league", "la_liga", "bundesliga", "serie_a", "ligue_1"]
        total_synced = 0

        for comp in competitions:
            try:
                fixtures = await client.get_fixtures(comp)
                for f in fixtures:
                    ext_id = str(f["external_id"])
                    stmt = select(Match).where(Match.external_id == ext_id)
                    existing = (await db.execute(stmt)).scalar_one_or_none()

                    if not existing:
                        new_match = Match(
                            external_id=ext_id,
                            home_team=f["home_team"]["name"],
                            away_team=f["away_team"]["name"],
                            league=f.get("competition", comp),
                            kickoff_time=datetime.fromisoformat(f["kickoff_time"].replace("Z", "+00:00")).replace(tzinfo=None),
                            status=f["status"].lower(),
                            source="footballdata",
                            sport="football"
                        )
                        db.add(new_match)

                        # Sync Teams
                        for t_data in [f["home_team"], f["away_team"]]:
                            t_ext_id = str(t_data["external_id"])
                            t_stmt = select(Team).where(Team.external_id == t_ext_id)
                            t_existing = (await db.execute(t_stmt)).scalar_one_or_none()
                            if not t_existing:
                                db.add(Team(
                                    external_id=t_ext_id,
                                    name=t_data["name"],
                                    short_name=t_data.get("short_name"),
                                    league=comp
                                ))

                        total_synced += 1
                await db.commit()
            except Exception as e:
                logger.error(f"Failed syncing league {comp} from FootballData: {e}")
                await db.rollback()

        return {"status": "success", "synced": total_synced, "provider": "footballdata"}

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

@router.post("/sync/odds-metadata")
async def sync_odds_metadata(
    league: str = Query("premier_league"),
    db: AsyncSession = Depends(get_db)
):
    """
    Syncs odds and market mappings from The Odds API.
    Useful for populating the market_mappings table for affiliate links.
    """
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ODDS_API_KEY not configured")

    client = OddsAPIClient(api_key)
    try:
        odds_list = await client.get_odds_for_competition(league)
        mappings_created = 0

        for odds in odds_list:
            # Find matching match in DB
            stmt = select(Match).where(
                Match.home_team == odds.home_team,
                Match.away_team == odds.away_team
            )
            match = (await db.execute(stmt)).scalars().first()

            if match:
                # Create mappings for 1x2 market
                for selection, price in [("home", odds.home_odds), ("draw", odds.draw_odds), ("away", odds.away_odds)]:
                    # Check if mapping exists
                    map_stmt = select(MarketMapping).where(
                        MarketMapping.match_id == match.id,
                        MarketMapping.provider_name == "theoddsapi",
                        MarketMapping.market_type == "1x2",
                        MarketMapping.selection_name == selection
                    )
                    existing_map = (await db.execute(map_stmt)).scalar_one_or_none()

                    if not existing_map:
                        db.add(MarketMapping(
                            match_id=match.id,
                            provider_name="theoddsapi",
                            external_match_id=odds.match_id,
                            external_selection_id=selection, # For The Odds API, selection is often the name
                            market_type="1x2",
                            selection_name=selection
                        ))
                        mappings_created += 1

        await db.commit()
        return {"status": "success", "mappings_created": mappings_created, "league": league}
    except Exception as e:
        logger.error(f"Failed syncing odds metadata for {league}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/competitions")
async def list_competitions():
    """List available competitions from iSports mapping."""
    return {"competitions": ISPORTS_LEAGUE_IDS}
