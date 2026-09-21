"""
TRACK-009: Global Search & Indexing
Universal multi-entity fuzzy lookup across the VIT ecosystem.

GET /api/search?q=<query>&types=users,matches,agents,academy,blockchain
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Match, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["Global Search"])

_ALL_TYPES = {"users", "matches", "agents", "academy", "blockchain", "predictions"}


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    types: str = Query(
        "users,matches,agents,academy",
        description="Comma-separated entity types to search",
    ),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Universal search across users, matches, AI agents, academy resources, and blockchain.
    Returns ranked results grouped by entity type.
    """
    q = q.strip()
    if not q:
        return {"query": q, "results": {}, "total": 0}

    requested = {t.strip().lower() for t in types.split(",")} & _ALL_TYPES
    results: Dict[str, List[Dict]] = {}
    total = 0

    # ── Users ──────────────────────────────────────────────────────────────
    if "users" in requested:
        try:
            rows = (
                await db.execute(
                    select(User.id, User.username, User.email, User.created_at)
                    .where(
                        or_(
                            func.lower(User.username).contains(q.lower()),
                            func.lower(User.email).contains(q.lower()),
                        )
                    )
                    .limit(limit)
                )
            ).all()
            hits = [
                {
                    "type": "user",
                    "id": r.id,
                    "label": r.username or r.email,
                    "sub": r.email,
                    "url": f"/api/identity/users/{r.id}",
                }
                for r in rows
            ]
            if hits:
                results["users"] = hits
                total += len(hits)
        except Exception as e:
            logger.warning("user search failed: %s", e)

    # ── Matches ────────────────────────────────────────────────────────────
    if "matches" in requested:
        try:
            rows = (
                await db.execute(
                    select(Match.id, Match.home_team, Match.away_team, Match.match_date, Match.league)
                    .where(
                        or_(
                            func.lower(Match.home_team).contains(q.lower()),
                            func.lower(Match.away_team).contains(q.lower()),
                            func.lower(Match.league).contains(q.lower()),
                        )
                    )
                    .order_by(Match.match_date.desc())
                    .limit(limit)
                )
            ).all()
            hits = [
                {
                    "type": "match",
                    "id": r.id,
                    "label": f"{r.home_team} vs {r.away_team}",
                    "sub": f"{r.league} · {str(r.match_date)[:10] if r.match_date else 'TBD'}",
                    "url": f"/api/matches/{r.id}",
                }
                for r in rows
            ]
            if hits:
                results["matches"] = hits
                total += len(hits)
        except Exception as e:
            logger.warning("match search failed: %s", e)

    # ── AI Agents ──────────────────────────────────────────────────────────
    if "agents" in requested:
        try:
            from app.modules.agent_registry.models import AIAgentRegistration
            rows = (
                await db.execute(
                    select(
                        AIAgentRegistration.agent_id,
                        AIAgentRegistration.name,
                        AIAgentRegistration.capabilities,
                        AIAgentRegistration.status,
                    )
                    .where(
                        or_(
                            func.lower(AIAgentRegistration.name).contains(q.lower()),
                            func.lower(AIAgentRegistration.agent_id).contains(q.lower()),
                            func.lower(AIAgentRegistration.capabilities).contains(q.lower()),
                        )
                    )
                    .limit(limit)
                )
            ).all()
            hits = [
                {
                    "type": "agent",
                    "id": r.agent_id,
                    "label": r.name,
                    "sub": f"Status: {r.status}",
                    "url": f"/api/agents/registry/{r.agent_id}",
                }
                for r in rows
            ]
            if hits:
                results["agents"] = hits
                total += len(hits)
        except Exception as e:
            logger.warning("agent search failed: %s", e)

    # ── Academy Resources ──────────────────────────────────────────────────
    if "academy" in requested:
        try:
            from app.modules.academy.models import AcademyResource
            rows = (
                await db.execute(
                    select(AcademyResource.id, AcademyResource.title, AcademyResource.resource_type, AcademyResource.category)
                    .where(
                        or_(
                            func.lower(AcademyResource.title).contains(q.lower()),
                            func.lower(AcademyResource.category).contains(q.lower()),
                        )
                    )
                    .limit(limit)
                )
            ).all()
            hits = [
                {
                    "type": "academy",
                    "id": r.id,
                    "label": r.title,
                    "sub": f"{r.resource_type} · {r.category}",
                    "url": f"/api/academy/resources/{r.id}",
                }
                for r in rows
            ]
            if hits:
                results["academy"] = hits
                total += len(hits)
        except Exception as e:
            logger.warning("academy search failed: %s", e)

    # ── Blockchain (delegate to explorer) ─────────────────────────────────
    if "blockchain" in requested:
        try:
            from app.core.kernel import kernel
            subsystem = kernel.get_subsystem("blockchain")
            if subsystem and hasattr(subsystem, "query_engine") and subsystem.query_engine:
                bc_result = await subsystem.query_engine.unified_search(db, q)
                if bc_result and bc_result.get("type") != "not_found":
                    results["blockchain"] = [
                        {
                            "type": "blockchain",
                            "id": q,
                            "label": bc_result.get("type", "blockchain entity"),
                            "sub": bc_result.get("hash") or bc_result.get("address") or q,
                            "url": f"/api/explorer/search?q={q}",
                            "data": bc_result,
                        }
                    ]
                    total += 1
        except Exception as e:
            logger.warning("blockchain search failed: %s", e)

    return {
        "query": q,
        "types_searched": list(requested),
        "results": results,
        "total": total,
    }


@router.get("/suggest")
async def search_suggestions(
    q: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Fast auto-complete suggestions — top 5 matches across users and teams.
    Optimized for low latency (no blockchain lookup).
    """
    q = q.strip().lower()
    suggestions: List[str] = []

    try:
        user_rows = (
            await db.execute(
                select(User.username)
                .where(func.lower(User.username).startswith(q))
                .limit(3)
            )
        ).scalars().all()
        suggestions.extend(user_rows)
    except Exception:
        pass

    try:
        match_rows = (
            await db.execute(
                select(Match.home_team, Match.away_team)
                .where(
                    or_(
                        func.lower(Match.home_team).startswith(q),
                        func.lower(Match.away_team).startswith(q),
                    )
                )
                .limit(3)
            )
        ).all()
        for r in match_rows:
            if r.home_team.lower().startswith(q):
                suggestions.append(r.home_team)
            if r.away_team.lower().startswith(q):
                suggestions.append(r.away_team)
    except Exception:
        pass

    # Deduplicate while preserving order
    seen: set = set()
    unique = []
    for s in suggestions:
        if s and s.lower() not in seen:
            seen.add(s.lower())
            unique.append(s)

    return {"query": q, "suggestions": unique[:8]}
