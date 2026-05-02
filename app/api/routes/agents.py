"""app/api/routes/agents.py — Autonomous agent status, control & reports endpoints."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.api.middleware.auth import verify_api_key

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/status")
async def agents_status(_user=Depends(verify_api_key)):
    """Full status snapshot for all autonomous agents."""
    try:
        from app.agents.coordinator import get_coordinator
        return get_coordinator().status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/summary")
async def agents_summary(_user=Depends(verify_api_key)):
    """Lightweight one-row-per-agent health summary."""
    try:
        from app.agents.coordinator import get_coordinator
        return get_coordinator().summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/trigger/{agent_name}")
async def trigger_agent(agent_name: str, _user=Depends(verify_api_key)):
    """Manually trigger an agent's next cycle immediately."""
    try:
        from app.agents.coordinator import get_coordinator
        ok = get_coordinator().trigger(agent_name)
        if not ok:
            valid = list(get_coordinator().status()["agents"].keys())
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_name}' not found. Valid: {', '.join(valid)}",
            )
        return {"triggered": agent_name, "status": "dispatched"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/providers")
async def ai_provider_status(_user=Depends(verify_api_key)):
    """Return availability, rate-limit state, and current priority order of all AI providers."""
    try:
        from app.services.ai_client import provider_status, get_provider_priority
        return {
            "providers": provider_status(),
            "priority": get_provider_priority(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/providers/refresh")
async def refresh_providers(_user=Depends(verify_api_key)):
    """
    Hot-reload AI provider config without restarting the server.

    Clears all rate-limit backoff state so every provider is immediately
    retried on the next agent cycle.  API keys are re-read from environment
    variables automatically on each call, so updating a secret in Replit
    and calling this endpoint is sufficient to activate a new key.
    """
    try:
        from app.services.ai_client import reset_provider_backoff, provider_status, get_provider_priority
        cleared = reset_provider_backoff()
        return {
            "refreshed": True,
            "cleared_backoffs": list(cleared.keys()),
            "providers": provider_status(),
            "priority": get_provider_priority(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class _ProviderPriorityBody(BaseModel):
    order: list[str]


@router.post("/providers/priority")
async def set_provider_priority_endpoint(body: _ProviderPriorityBody, _user=Depends(verify_api_key)):
    """
    Update the AI provider try-order without restarting the server.

    Pass a list of provider names in the desired priority order.
    Valid names: gemini, claude, openai, grok.
    Unknown names are ignored; missing names are appended at the end.
    """
    try:
        from app.services.ai_client import set_provider_priority, provider_status
        new_order = set_provider_priority(body.order)
        return {
            "updated": True,
            "priority": new_order,
            "providers": provider_status(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/result/{agent_name}")
async def agent_last_result(agent_name: str, _user=Depends(verify_api_key)):
    """Return the last_result dict for a specific agent."""
    try:
        from app.agents.coordinator import get_coordinator
        result = get_coordinator().get_agent_result(agent_name)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_name}' not found or has no result yet",
            )
        return {"agent": agent_name, "result": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/reports")
async def agent_reports(
    limit: int = Query(50, ge=1, le=200),
    agent: Optional[str] = Query(None),
    insight_type: Optional[str] = Query(None),
    _user=Depends(verify_api_key),
):
    """
    Return recent AgentInsight records — the live intelligence feed.

    Query params:
      limit        — max rows (default 50, max 200)
      agent        — filter by agent_name  (e.g. match-scout, news-sentinel)
      insight_type — filter by insight_type (e.g. match_scout, team_news, daily_brief)
    """
    try:
        from app.db.database import AsyncSessionLocal
        from app.db.models import AgentInsight
        from sqlalchemy import select, desc

        async with AsyncSessionLocal() as db:
            q = select(AgentInsight).order_by(desc(AgentInsight.created_at)).limit(limit)
            if agent:
                q = q.where(AgentInsight.agent_name == agent)
            if insight_type:
                q = q.where(AgentInsight.insight_type == insight_type)
            rows = (await db.execute(q)).scalars().all()

        return {
            "count": len(rows),
            "reports": [
                {
                    "id":           r.id,
                    "agent_name":   r.agent_name,
                    "insight_type": r.insight_type,
                    "match_id":     r.match_id,
                    "team":         getattr(r, "team", None),
                    "content":      r.content,
                    "meta":         r.meta,
                    "confidence":   float(r.confidence) if r.confidence else None,
                    "ai_provider":  r.ai_provider,
                    "created_at":   r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/generate-now")
async def generate_reports_now(_user=Depends(verify_api_key)):
    """
    Trigger all intelligence agents immediately and return how many were dispatched.

    Useful for seeding the Intelligence Reports page on first deployment or
    after a long idle period.  Agents run asynchronously — reports appear in
    /agents/reports within ~30 seconds.
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)
    try:
        from app.agents.coordinator import get_coordinator
        coordinator = get_coordinator()
        intelligence_agents = [
            "analytics-reporter",
            "match-scout",
            "news-sentinel",
            "odds-anomaly",
        ]
        triggered = []
        skipped   = []
        for name in intelligence_agents:
            try:
                ok = coordinator.trigger(name)
                if ok:
                    triggered.append(name)
                else:
                    _log.warning("[generate-now] agent '%s' not found in registry", name)
                    skipped.append(name)
            except Exception as agent_exc:
                _log.error("[generate-now] error triggering agent '%s': %s", name, agent_exc, exc_info=True)
                skipped.append(name)

        if not triggered:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"No agents were triggered — {len(skipped)} agent(s) not ready yet. "
                    "The background supervisor may still be starting up. Try again in a few seconds."
                ),
            )

        return {
            "triggered":       triggered,
            "skipped":         skipped,
            "message":         f"Dispatched {len(triggered)} agent(s) — reports will appear within ~30 seconds",
        }
    except HTTPException:
        raise
    except Exception as exc:
        _log.error("[generate-now] unexpected error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/network")
async def agents_network_summary(_user=Depends(verify_api_key)):
    """Network-focused summary: node IDs, contribution scores, DID identifiers."""
    try:
        from app.agents.coordinator import get_coordinator
        return get_coordinator().network_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/live-scores")
async def live_scores(_user=Depends(verify_api_key)):
    """Return current live match scores from the database."""
    try:
        from app.db.database import AsyncSessionLocal
        from app.db.models import Match
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            rows = await db.execute(
                select(Match).where(
                    Match.status.in_(["live", "in_play"]),
                    Match.actual_outcome.is_(None),
                )
            )
            live = rows.scalars().all()

        return {
            "live_count": len(live),
            "matches": [
                {
                    "id":         m.id,
                    "home_team":  m.home_team,
                    "away_team":  m.away_team,
                    "league":     m.league,
                    "home_score": m.home_goals,
                    "away_score": m.away_goals,
                    "status":     m.status,
                    "kickoff":    m.kickoff_time.isoformat() if m.kickoff_time else None,
                }
                for m in live
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
