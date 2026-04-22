"""
Module F — ETL Pipeline
Fetch → Clean → Normalize → Feature Engineer → Store

Runs every 6 hours via a background asyncio task registered in main.py.
Also provides a lightweight odds-only refresh that updates the feature store
and broadcasts changes to connected WebSocket clients.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.data.models import MatchFeatureStore, PipelineRun
from app.data.feature_engineering import engineer_features, compute_source_quality, PIPELINE_VERSION
from app.data.realtime import odds_manager
from app.core.dependencies import get_data_loader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPPORTED_LEAGUES = [
    "premier_league",
    "la_liga",
    "bundesliga",
    "serie_a",
    "ligue_1",
    "eredivisie",
    "primeira_liga",
]

ETL_INTERVAL_HOURS = 6
ODDS_REFRESH_INTERVAL_MINUTES = 15
DAYS_AHEAD = 14         # fetch fixtures up to 14 days out (tomorrow + 14d window)
STALE_AFTER_HOURS = 25  # mark as stale when kickoff has passed by this margin

# ---------------------------------------------------------------------------
# Background loops (registered from main.py)
# ---------------------------------------------------------------------------

def _has_data_api_key() -> bool:
    """Return True only when at least one football data API key is configured."""
    return bool(
        os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
        or os.getenv("RAPIDAPI_KEY", "").strip()
    )


async def etl_pipeline_loop():
    """Full ETL run every 6 hours — skips gracefully when no API key is set."""
    await asyncio.sleep(30)   # allow server to fully start first
    while True:
        if not _has_data_api_key():
            logger.info("[pipeline] No football data API key configured — skipping ETL run")
        else:
            try:
                logger.info("[pipeline] Starting scheduled ETL run")
                result = await run_full_etl(run_type="scheduled")
                logger.info(
                    f"[pipeline] ETL complete — upserted={result['matches_upserted']} "
                    f"skipped={result['matches_skipped']} errors={len(result['errors'])}"
                )
            except Exception as e:
                logger.error(f"[pipeline] ETL loop error: {e}", exc_info=True)
        await asyncio.sleep(ETL_INTERVAL_HOURS * 3600)


async def odds_refresh_loop():
    """Lightweight odds-only refresh every 15 minutes — skips when no API key."""
    await asyncio.sleep(90)   # start after ETL warmup
    while True:
        if not _has_data_api_key():
            logger.debug("[pipeline] No API key — skipping odds refresh")
        else:
            try:
                await run_odds_refresh()
            except Exception as e:
                logger.error(f"[pipeline] Odds refresh error: {e}", exc_info=True)
        await asyncio.sleep(ODDS_REFRESH_INTERVAL_MINUTES * 60)


# ---------------------------------------------------------------------------
# Full ETL
# ---------------------------------------------------------------------------

async def run_full_etl(run_type: str = "manual") -> Dict[str, Any]:
    """
    Execute the complete Fetch → Clean → Normalize → Feature Engineer → Store pipeline
    for all supported leagues.
    """
    started_at = datetime.now(timezone.utc)
    run_log = PipelineRun(
        run_type=run_type,
        status="running",
        leagues_processed=[],
        matches_upserted=0,
        matches_skipped=0,
        errors=[],
    )

    async with AsyncSessionLocal() as db:
        db.add(run_log)
        await db.commit()
        await db.refresh(run_log)
        run_id = run_log.id

    await odds_manager.broadcast_pipeline_event("run_started", run_type=run_type)

    total_upserted = total_skipped = 0
    all_errors: List[str] = []
    processed_leagues: List[str] = []

    loader = get_data_loader()
    if loader is None:
        msg = "DataLoader unavailable — FOOTBALL_DATA_API_KEY may not be set"
        logger.warning(f"[pipeline] {msg}")
        await _finalize_run(run_id, "failed", [], 0, 0, [msg], started_at)
        return {"status": "failed", "errors": [msg], "matches_upserted": 0, "matches_skipped": 0}

    for i, league in enumerate(SUPPORTED_LEAGUES):
        if i > 0:
            await asyncio.sleep(3)   # brief pause between leagues to respect API rate limits
        try:
            upserted, skipped, errors = await _process_league(loader, league)
            total_upserted += upserted
            total_skipped += skipped
            all_errors.extend(errors)
            processed_leagues.append(league)
            logger.info(f"[pipeline] {league}: upserted={upserted} skipped={skipped}")
        except Exception as e:
            err = f"{league}: {e}"
            logger.error(f"[pipeline] Failed league {err}", exc_info=True)
            all_errors.append(err)

    # Mark stale records
    await _mark_stale_records()

    status = "success" if not all_errors else ("partial" if total_upserted > 0 else "failed")
    await _finalize_run(run_id, status, processed_leagues, total_upserted, total_skipped, all_errors, started_at)

    await odds_manager.broadcast_pipeline_event(
        "run_complete",
        matches=total_upserted,
        leagues=processed_leagues,
        errors=len(all_errors),
    )

    return {
        "status": status,
        "run_id": run_id,
        "matches_upserted": total_upserted,
        "matches_skipped": total_skipped,
        "leagues": processed_leagues,
        "errors": all_errors,
    }


async def _process_league(loader, league: str) -> Tuple[int, int, List[str]]:
    """Run the full ETL pipeline for one league."""
    upserted = skipped = 0
    errors: List[str] = []

    # --- FETCH ---
    try:
        context = await loader.fetch_all_context(
            competition=league,
            days_ahead=DAYS_AHEAD,
            include_recent_form=True,
            include_h2h=True,
            include_odds=True,
        )
    except Exception as e:
        return 0, 0, [f"fetch failed: {e}"]

    if context.is_empty():
        return 0, 0, []

    # --- PROCESS each fixture ---
    async with AsyncSessionLocal() as db:
        for fixture in context.fixtures:
            try:
                result = await _upsert_fixture(
                    db, fixture, context.standings, context.injuries,
                    context.recent_form, context.head_to_head, league
                )
                if result:
                    upserted += 1
                else:
                    skipped += 1
            except Exception as e:
                err = f"fixture {fixture.get('external_id', '?')}: {e}"
                errors.append(err)
                logger.warning(f"[pipeline] {err}")
        await db.commit()

    return upserted, skipped, errors


async def _upsert_fixture(
    db: AsyncSession,
    fixture: Dict,
    standings: Dict,
    injuries: List[Dict],
    recent_form: Dict,
    head_to_head: Dict,
    league: str,
) -> bool:
    """
    Feature-engineer one fixture and upsert into MatchFeatureStore.
    Returns True if a new record was created, False if updated.
    """
    external_id = str(fixture.get("external_id", ""))
    if not external_id:
        return False

    home_team = fixture.get("home_team", {}).get("name", "")
    away_team = fixture.get("away_team", {}).get("name", "")
    kickoff_raw = fixture.get("utc_date") or fixture.get("kickoff_time")
    kickoff_time: Optional[datetime] = None
    if kickoff_raw:
        try:
            kickoff_time = datetime.fromisoformat(str(kickoff_raw).replace("Z", "+00:00"))
        except Exception:
            pass

    # --- CLEAN: skip if no teams ---
    if not home_team or not away_team:
        return False

    odds_data = fixture.get("odds")

    # --- NORMALIZE & FEATURE ENGINEER ---
    features = engineer_features(
        fixture=fixture,
        standings=standings,
        injuries=injuries,
        odds_data=odds_data,
        recent_form=recent_form,
        head_to_head=head_to_head,
    )

    quality = compute_source_quality(features)

    # --- STORE (upsert) ---
    existing = (
        await db.execute(select(MatchFeatureStore).where(MatchFeatureStore.match_id == external_id))
    ).scalar_one_or_none()

    is_new = existing is None

    if is_new:
        record = MatchFeatureStore(
            match_id=external_id,
            home_team=home_team,
            away_team=away_team,
            league=league,
            kickoff_time=kickoff_time,
            features=features,
            odds_snapshot=odds_data,
            injury_snapshot=[i for i in injuries if home_team.lower() in str(i.get("team", "")).lower()
                             or away_team.lower() in str(i.get("team", "")).lower()],
            source_quality=quality,
            pipeline_version=PIPELINE_VERSION,
            is_stale=False,
        )
        db.add(record)
    else:
        existing.features = features
        existing.odds_snapshot = odds_data
        existing.source_quality = quality
        existing.pipeline_version = PIPELINE_VERSION
        existing.is_stale = False
        if kickoff_time:
            existing.kickoff_time = kickoff_time

    # Broadcast feature-ready to WebSocket clients
    asyncio.create_task(odds_manager.broadcast_feature_ready(external_id, league))

    return is_new


# ---------------------------------------------------------------------------
# Odds-only refresh
# ---------------------------------------------------------------------------

async def run_odds_refresh() -> Dict[str, Any]:
    """
    Fetch only odds data and update the odds_snapshot field + market features.
    Much faster than a full ETL run.
    """
    loader = get_data_loader()
    if not loader:
        return {"status": "skipped", "reason": "no loader"}

    updated = 0
    for i, league in enumerate(SUPPORTED_LEAGUES):
        if i > 0:
            await asyncio.sleep(2)   # throttle between leagues to avoid rate limit floods
        try:
            odds_list = await loader.fetch_odds_only(league, days_ahead=DAYS_AHEAD)
            if not odds_list:
                continue

            async with AsyncSessionLocal() as db:
                for odds in odds_list:
                    if not odds.match_id:
                        continue

                    record = (
                        await db.execute(
                            select(MatchFeatureStore).where(
                                MatchFeatureStore.match_id == str(odds.match_id)
                            )
                        )
                    ).scalar_one_or_none()

                    if record is None:
                        continue

                    odds_snapshot = {
                        "home": odds.home_odds,
                        "draw": odds.draw_odds,
                        "away": odds.away_odds,
                        "over_25": odds.over_25_odds,
                        "btts_yes": odds.btts_yes_odds,
                        "bookmaker": odds.bookmaker,
                        "overround": odds.overround(),
                        "vig_free_probs": odds.vig_free_probabilities(),
                    }

                    # Patch market features in the existing feature dict
                    from app.data.feature_engineering import _market_features
                    market_patch = _market_features(odds_snapshot)
                    updated_features = dict(record.features or {})
                    updated_features.update(market_patch)

                    record.odds_snapshot = odds_snapshot
                    record.features = updated_features

                    await db.commit()
                    updated += 1

                    # Broadcast to WebSocket subscribers
                    asyncio.create_task(
                        odds_manager.broadcast_odds_update(str(odds.match_id), league, odds_snapshot)
                    )

        except Exception as e:
            logger.warning(f"[pipeline] Odds refresh failed for {league}: {e}")

    logger.info(f"[pipeline] Odds refresh complete — {updated} records updated")
    return {"status": "success", "updated": updated}


# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------

async def _mark_stale_records():
    """Flag feature records whose kickoff has already passed."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=STALE_AFTER_HOURS)
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(MatchFeatureStore)
            .where(MatchFeatureStore.kickoff_time < cutoff)
            .where(MatchFeatureStore.is_stale == False)
            .values(is_stale=True)
        )
        await db.commit()


async def _finalize_run(
    run_id: int,
    status: str,
    leagues: List[str],
    upserted: int,
    skipped: int,
    errors: List[str],
    started_at: datetime,
):
    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()
    async with AsyncSessionLocal() as db:
        run = (await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))).scalar_one_or_none()
        if run:
            run.status = status
            run.leagues_processed = leagues
            run.matches_upserted = upserted
            run.matches_skipped = skipped
            run.errors = errors
            run.duration_seconds = round(duration, 2)
            run.finished_at = finished_at
            await db.commit()


# ---------------------------------------------------------------------------
# Status helper (used by routes)
# ---------------------------------------------------------------------------

async def get_pipeline_status() -> Dict[str, Any]:
    """Return current pipeline health and statistics."""
    async with AsyncSessionLocal() as db:
        last_run = (
            await db.execute(
                select(PipelineRun)
                .where(PipelineRun.status != "running")
                .order_by(PipelineRun.started_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        total_features = (
            await db.execute(select(MatchFeatureStore))
        ).scalars().all()

        active = [r for r in total_features if not r.is_stale]
        stale = [r for r in total_features if r.is_stale]

    return {
        "pipeline_version": PIPELINE_VERSION,
        "supported_leagues": SUPPORTED_LEAGUES,
        "etl_interval_hours": ETL_INTERVAL_HOURS,
        "odds_refresh_interval_minutes": ODDS_REFRESH_INTERVAL_MINUTES,
        "websocket_connections": odds_manager.connection_count,
        "feature_store": {
            "total_records": len(total_features),
            "active_records": len(active),
            "stale_records": len(stale),
        },
        "last_run": {
            "id": last_run.id if last_run else None,
            "status": last_run.status if last_run else None,
            "run_type": last_run.run_type if last_run else None,
            "matches_upserted": last_run.matches_upserted if last_run else None,
            "duration_seconds": last_run.duration_seconds if last_run else None,
            "started_at": last_run.started_at.isoformat() if last_run else None,
            "finished_at": last_run.finished_at.isoformat() if last_run and last_run.finished_at else None,
        } if last_run else None,
    }
