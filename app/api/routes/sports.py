from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging
import os
from datetime import datetime, timezone

from app.db.database import get_db
from app.db.models import Match, Team
from app.modules.sports.models import MarketMapping
from app.services.isports_api import ISportsClient, ISPORTS_LEAGUE_IDS
from app.services.football_api import FootballDataClient
from app.services.odds_api import OddsAPIClient

router = APIRouter(prefix="/sports", tags=["sports-infra"])
logger = logging.getLogger(__name__)


# ── Sync status ───────────────────────────────────────────────────────────────

@router.get("/sync/status")
async def get_sync_status(db: AsyncSession = Depends(get_db)):
    """
    Return which sports API providers are configured and the current match count.
    Useful for the frontend to know whether a sync is needed.
    """
    providers = {
        "isports":      bool(os.getenv("ISPORTS_API_KEY")),
        "footballdata": bool(os.getenv("FOOTBALL_DATA_API_KEY")),
        "theoddsapi":   bool(os.getenv("ODDS_API_KEY")),
    }
    total_matches = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    upcoming = (
        await db.execute(
            select(func.count(Match.id))
            .where(Match.actual_outcome.is_(None))
            .where(Match.kickoff_time >= datetime.now(timezone.utc).replace(tzinfo=None))
        )
    ).scalar() or 0

    configured = [k for k, v in providers.items() if v]
    return {
        "providers": providers,
        "configured": configured,
        "any_configured": bool(configured),
        "total_matches_in_db": total_matches,
        "upcoming_matches": upcoming,
        "sync_recommended": upcoming == 0 and bool(configured),
    }


# ── Fixture sync ──────────────────────────────────────────────────────────────

@router.post("/sync/fixtures")
async def sync_sports_fixtures(
    provider: str = Query("isports", description="Provider to sync from: isports, footballdata"),
    league_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronises fixtures from external sports providers.
    Returns the number of new fixtures synced.
    """
    if provider == "isports":
        isports_key = os.getenv("ISPORTS_API_KEY")
        if not isports_key:
            raise HTTPException(status_code=500, detail="ISPORTS_API_KEY not configured")

        client = ISportsClient(isports_key)
        leagues_to_sync = dict(ISPORTS_LEAGUE_IDS)
        if league_id:
            leagues_to_sync = {k: v for k, v in leagues_to_sync.items() if v == league_id}

        total_synced = 0
        errors: List[str] = []

        for name, lid in leagues_to_sync.items():
            try:
                raw_matches = await client.get_fixtures_and_results(lid)
                for m in raw_matches:
                    # Only sync upcoming/scheduled fixtures (status 0 = Not Started)
                    if str(m.get("status")) not in ("0", "not_started", "scheduled"):
                        continue
                    formatted = client.format_match_data(m, name)
                    ext_id = str(m.get("matchId") or m.get("id", ""))
                    if not ext_id:
                        continue

                    stmt = select(Match).where(Match.external_id == ext_id)
                    existing = (await db.execute(stmt)).scalar_one_or_none()
                    if existing:
                        # Update kickoff time if changed
                        new_kickoff = formatted.get("kickoff_time")
                        if new_kickoff and existing.kickoff_time != new_kickoff:
                            existing.kickoff_time = new_kickoff
                        continue

                    new_match = Match(
                        external_id=ext_id,
                        home_team=formatted.get("home_team", ""),
                        away_team=formatted.get("away_team", ""),
                        league=formatted.get("league", name),
                        sport=formatted.get("sport", "football"),
                        kickoff_time=formatted.get("kickoff_time"),
                        status=formatted.get("status", "scheduled"),
                    )
                    db.add(new_match)
                    total_synced += 1

            except Exception as exc:
                logger.warning("Failed syncing league %s (%s): %s", name, lid, exc)
                errors.append(f"{name}: {exc}")

        await db.commit()
        return {
            "status": "success",
            "provider": "isports",
            "total_synced": total_synced,
            "leagues_attempted": len(leagues_to_sync),
            "errors": errors,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    elif provider == "footballdata":
        api_key = os.getenv("FOOTBALL_DATA_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="FOOTBALL_DATA_API_KEY not configured")

        client = FootballDataClient(api_key)
        total_synced = 0
        errors: List[str] = []

        try:
            matches_data = await client.get_upcoming_matches()
            for m in (matches_data if isinstance(matches_data, list) else []):
                ext_id = str(m.get("id", ""))
                if not ext_id:
                    continue
                stmt = select(Match).where(Match.external_id == ext_id)
                existing = (await db.execute(stmt)).scalar_one_or_none()
                if existing:
                    continue
                home = m.get("homeTeam", {})
                away = m.get("awayTeam", {})
                competition = m.get("competition", {})
                new_match = Match(
                    external_id=ext_id,
                    home_team=home.get("name", home.get("shortName", "")),
                    away_team=away.get("name", away.get("shortName", "")),
                    league=competition.get("name", ""),
                    sport="football",
                    kickoff_time=m.get("utcDate"),
                    status=m.get("status", "scheduled").lower(),
                )
                db.add(new_match)
                total_synced += 1
        except Exception as exc:
            logger.error("Football-Data sync error: %s", exc)
            errors.append(str(exc))

        await db.commit()
        return {
            "status": "success",
            "provider": "footballdata",
            "total_synced": total_synced,
            "errors": errors,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}. Use 'isports' or 'footballdata'.")


# ── Odds metadata sync ────────────────────────────────────────────────────────

@router.post("/sync/odds-metadata")
async def sync_odds_metadata(
    league: str = Query(..., description="League slug e.g. soccer_epl"),
    db: AsyncSession = Depends(get_db),
):
    """Sync market mapping metadata from The Odds API for a given league."""
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ODDS_API_KEY not configured")

    client = OddsAPIClient(api_key)
    try:
        odds_list = await client.get_odds_for_competition(league)
        mappings_created = 0

        for odds in odds_list:
            stmt = select(Match).where(
                Match.home_team == odds.home_team,
                Match.away_team == odds.away_team,
            )
            match = (await db.execute(stmt)).scalars().first()
            if not match:
                continue

            for selection, price in [("home", odds.home_odds), ("draw", odds.draw_odds), ("away", odds.away_odds)]:
                map_stmt = select(MarketMapping).where(
                    MarketMapping.match_id == match.id,
                    MarketMapping.provider_name == "theoddsapi",
                    MarketMapping.market_type == "1x2",
                    MarketMapping.selection_name == selection,
                )
                if not (await db.execute(map_stmt)).scalar_one_or_none():
                    db.add(MarketMapping(
                        match_id=match.id,
                        provider_name="theoddsapi",
                        external_match_id=odds.match_id,
                        external_selection_id=selection,
                        market_type="1x2",
                        selection_name=selection,
                    ))
                    mappings_created += 1

        await db.commit()
        return {
            "status": "success",
            "mappings_created": mappings_created,
            "league": league,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("Failed syncing odds metadata for %s: %s", league, exc)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


# ── Meta ──────────────────────────────────────────────────────────────────────

@router.get("/competitions")
async def list_competitions():
    """List available competitions from iSports mapping."""
    return {"competitions": ISPORTS_LEAGUE_IDS}


@router.get("/providers")
async def list_providers():
    """Return configured sports data providers (keys existence only, not values)."""
    return {
        "providers": {
            "isports":      {"configured": bool(os.getenv("ISPORTS_API_KEY")),      "label": "iSports API"},
            "footballdata": {"configured": bool(os.getenv("FOOTBALL_DATA_API_KEY")), "label": "Football-Data.org"},
            "theoddsapi":   {"configured": bool(os.getenv("ODDS_API_KEY")),          "label": "The Odds API"},
        }
    }
