from __future__ import annotations
import logging
import asyncio
import os
import re
import json
from typing import List, Optional, Any, Dict, Union
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.api.middleware.auth import verify_api_key
from app.db.database import get_db
from app.modules.ai.copilot import AICopilot
from app.core.dependencies import get_orchestrator
from app.db.models import Match
from app.services.assistant_tools import TOOL_MAP, NATIVE_AI_TOOLS
from app.modules.ai.svi import SyntheticValueIndex
from app.services.ai_client import call_ai

router = APIRouter(prefix="/ai/assistant", tags=["ai-assistant"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None
    context: Optional[str] = None

async def _get_system_health_internal(db: AsyncSession) -> Dict[str, Any]:
    from sqlalchemy import select, func
    try:
        match_count = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    except Exception:
        match_count = 0

    orch = get_orchestrator()
    models_ready = orch.num_models_ready() if orch else 0

    # Try to get SVI
    try:
        svi_report = await SyntheticValueIndex.get_market_health_report(db)
        svi_val = svi_report.get("svi", 0)
        svi_status = svi_report.get("status", "unknown")
    except Exception:
        svi_val = 0
        svi_status = "unavailable"

    return {
        "status": "operational",
        "matches_in_db": match_count,
        "ai_models_ready": models_ready,
        "system_version": "5.5.0",
        "svi": svi_val,
        "svi_status": svi_status
    }

async def _handle_agentic_query(
    message: str,
    db: AsyncSession,
    history: Optional[List[dict]] = None,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    msg = message.lower()
    thoughts = ["Initiating VIT Native Intelligence", "Accessing internal neural matrix"]

    # 1. Market Intelligence & SVI
    if any(k in msg for k in ["svi", "market health", "collateral", "inflation", "trends", "clv"]):
        thoughts.append("Querying Synthetic Value Index & Market Trends")
        try:
            from exchange.order_book import OrderBook
            report = await AICopilot.get_market_copilot_report(db, OrderBook(), [], {}, {})
            svi_report = await SyntheticValueIndex.get_market_health_report(db)

            insights = "\n".join([f"- {i}" for i in report.get("insights", [])])
            reply = (
                f"### VIT Market Intelligence\n\n"
                f"**Synthetic Value Index (SVI):** {svi_report['svi']:.4f} ({svi_report['status']})\n"
                f"**Market Status:** The system is currently in a {svi_report['status']} state based on collateral-to-supply ratios.\n\n"
                f"**Core Insights:**\n{insights or '- No immediate anomalies detected.'}\n"
            )

            if "get_market_trends" in TOOL_MAP:
                trends = await TOOL_MAP["get_market_trends"]()
                if trends and "overall_avg_clv" in trends:
                    reply += f"\n**Network CLV:** {trends['overall_avg_clv']:.4f} | **Tracked Events:** {trends['total_bets']}"

            return {"available": True, "reply": reply, "thoughts": thoughts}
        except Exception as e:
            logger.error(f"SVI tool error: {e}")
            reply = "Market intelligence engine is re-calibrating. Please try again in a moment."
            return {"available": True, "reply": reply, "thoughts": thoughts}

    # 2. System Health & Agent Status
    if any(k in msg for k in ["health", "status", "ready", "models", "agents", "guardian"]):
        thoughts.append("Auditing VIT Agent Network")
        health = await _get_system_health_internal(db)

        reply = (
            f"### VIT Network Status: {health['status'].upper()}\n"
            f"- **Intelligence Level:** v{health['system_version']}\n"
            f"- **Active ML Models:** {health['ai_models_ready']} (Ensemble ready)\n"
            f"- **Database Density:** {health['matches_in_db']} matches indexed\n"
            f"- **SVI Stability:** {health['svi']:.4f}\n"
        )

        if "get_system_health" in TOOL_MAP:
            agent_health = await TOOL_MAP["get_system_health"]()
            if agent_health and "agents" in agent_health:
                reply += f"- **Live Agents:** {len(agent_health['agents'])} operational\n"
                active_agents = [a['name'] for a in agent_health['agents'] if a['status'] == 'ok']
                if active_agents:
                    reply += f"\n**Critical Systems:** {', '.join(active_agents[:4])} are online."

        return {"available": True, "reply": reply, "thoughts": thoughts}

    # 3. Sports Analysis
    if any(k in msg for k in ["match", "game", "soccer", "football", "prediction", "odds", "scores", "fixture"]):
        thoughts.append("Executing Sports Intelligence Toolset")

        match_id_search = re.search(r'(?:id\s*[:#]?\s*|match\s+)(\d+)', msg)
        if match_id_search:
            match_id = int(match_id_search.group(1))
            insights = await TOOL_MAP["get_match_insights"](match_id)
            if "error" not in insights:
                m = insights["match"]
                preds = insights["predictions"]
                reply = f"### Tactical Insight: {m['home_team']} vs {m['away_team']}\n"
                reply += f"*League: {m['league']} | Kickoff: {m['kickoff_time']}*\n\n"
                if preds:
                    p = preds[0]
                    reply += (
                        f"**Native Ensemble Forecast:**\n"
                        f"- Home Win: {p['home_prob']*100:.1f}%\n"
                        f"- Draw: {p['draw_prob']*100:.1f}%\n"
                        f"- Away Win: {p['away_prob']*100:.1f}%\n"
                        f"- **Confidence:** {p.get('confidence', 0)*100:.1f}%\n"
                    )
                else:
                    reply += "AI Models are currently processing this match. No prediction recorded yet."
                return {"available": True, "reply": reply, "thoughts": thoughts}

        upcoming = await TOOL_MAP["get_upcoming_matches"](limit=5)
        if upcoming:
            match_list = "\n".join([
                f"- **{m['home_team']} vs {m['away_team']}** (ID: {m['id']}) | {m['league']}"
                for m in upcoming
            ])
            reply = (
                f"### Upcoming Network Fixtures\n"
                f"I found the following matches in the VIT database:\n\n{match_list}\n\n"
                f"Ask me for 'insight on match [ID]' for a deep dive analysis."
            )
            return {"available": True, "reply": reply, "thoughts": thoughts}

    # 4. Native Natural Language Generation
    thoughts.append("Generating response via VIT Native NLP layer")
    reply = await call_ai(message)
    return {"available": True, "reply": reply, "thoughts": thoughts}

@router.post("/chat")
async def assistant_chat(body: ChatRequest, db: AsyncSession = Depends(get_db), _user=Depends(verify_api_key)):
    try:
        return await _handle_agentic_query(body.message, db, history=body.history, context=body.context)
    except Exception as e:
        logger.error(f"Assistant chat error: {e}", exc_info=True)
        return {
            "available": True,
            "reply": "The VIT Bot is temporarily unavailable. Please try again later.",
            "thoughts": ["Error encountered"],
        }

@router.get("/status")
async def assistant_status(db: AsyncSession = Depends(get_db), _user=Depends(verify_api_key)):
    health = await _get_system_health_internal(db)
    return {
        "available": True,
        "backend_ai_available": True,
        "provider": "native",
        "llm_configured": True,
        "message": f"VIT Bot v{health['system_version']} ready.",
        "health": health,
    }
