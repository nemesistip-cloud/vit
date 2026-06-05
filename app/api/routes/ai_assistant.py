from __future__ import annotations
import logging
import asyncio
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import verify_api_key
from app.db.database import get_db
from app.modules.ai.copilot import AICopilot
from app.core.dependencies import get_orchestrator
from app.db.models import Match
from app.services.assistant_tools import TOOL_MAP, NATIVE_AI_TOOLS

router = APIRouter(prefix="/ai/assistant", tags=["ai-assistant"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None
    context: Optional[str] = None

async def _get_system_health_internal(db: AsyncSession) -> Dict[str, Any]:
    from sqlalchemy import select, func
    match_count = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    orch = get_orchestrator()
    models_ready = orch.num_models_ready() if orch else 0
    return {
        "status": "operational",
        "matches_in_db": match_count,
        "ai_models_ready": models_ready,
        "system_version": "5.2.0"
    }

async def _handle_agentic_query(message: str, db: AsyncSession) -> Dict[str, Any]:
    msg = message.lower()
    thoughts = ["Analyzing intent", "Scanning system context"]

    # 1. Market Intelligence / SVI Queries
    if any(k in msg for k in ["svi", "market health", "collateral", "inflation", "trends", "clv"]):
        thoughts.append("Fetching Synthetic Value Index and Market Trends")
        from exchange.order_book import OrderBook
        report = await AICopilot.get_market_copilot_report(db, OrderBook(), [], {}, {})

        # Also try to get market trends tool
        trends = {}
        if "get_market_trends" in TOOL_MAP:
             trends = await TOOL_MAP["get_market_trends"]()

        insights = "\n".join([f"- {i}" for i in report["insights"]])
        reply = f"### Market Intelligence Report\n\n{insights}\n\n**SVI Status:** {report['svi'].get('status', 'healthy')}\n"
        if trends and "overall_avg_clv" in trends:
            reply += f"**Overall Avg CLV:** {trends['overall_avg_clv']:.4f}\n**Total Bets Tracked:** {trends['total_bets']}"

        return {
            "available": True,
            "reply": reply,
            "thoughts": thoughts
        }

    # 2. System Health / Status
    if any(k in msg for k in ["health", "status", "ready", "models", "agents"]):
        thoughts.append("Querying system health and agent status")
        health = await _get_system_health_internal(db)

        # Try agent tool
        agent_health = {}
        if "get_system_health" in TOOL_MAP:
            agent_health = await TOOL_MAP["get_system_health"]()

        reply = f"### System Status: {health['status'].upper()}\n- **Version:** {health['system_version']}\n- **AI Models:** {health['ai_models_ready']} active\n- **Total Matches:** {health['matches_in_db']}\n"
        if agent_health and "agents" in agent_health:
            reply += f"- **Active Agents:** {len(agent_health['agents'])}\n"

        return {
            "available": True,
            "reply": reply,
            "thoughts": thoughts
        }

    # 3. Sports Analysis & Odds
    if any(k in msg for k in ["match", "game", "soccer", "football", "prediction", "odds", "scores"]):
        thoughts.append("Processing sports data request")

        if "odds" in msg and "get_live_odds" in TOOL_MAP:
             # Just a sample league for demonstration
             odds_data = await TOOL_MAP["get_live_odds"]("premier_league")
             if "odds" in odds_data:
                 match = odds_data["odds"][0]
                 return {
                     "available": True,
                     "reply": f"I found live odds for **{match['home_team']} vs {match['away_team']}**:\n- Home: {match['home_odds']}\n- Draw: {match['draw_odds']}\n- Away: {match['away_odds']}\n(Source: {match['bookmaker']})",
                     "thoughts": thoughts
                 }

        from sqlalchemy import select
        from datetime import datetime
        result = await db.execute(select(Match).where(Match.kickoff_time > datetime.utcnow()).limit(3))
        matches = result.scalars().all()
        if matches:
            match_list = "\n".join([f"- **{m.home_team} vs {m.away_team}** (ID: {m.id}, {m.kickoff_time.strftime('%Y-%m-%d %H:%M')})" for m in matches])
            return {
                "available": True,
                "reply": f"I found some upcoming matches in the VIT database:\n\n{match_list}\n\nYou can ask for detailed insights using a match ID.",
                "thoughts": thoughts
            }

    # 4. Specific Match Insight
    if "insight" in msg or "analyze" in msg:
        import re
        match_id_search = re.search(r'id\s*(\d+)', msg)
        if match_id_search and "get_match_insights" in TOOL_MAP:
            match_id = int(match_id_search.group(1))
            thoughts.append(f"Fetching deep insights for match {match_id}")
            insights = await TOOL_MAP["get_match_insights"](match_id)
            if "error" not in insights:
                 m = insights["match"]
                 preds = insights["predictions"]
                 reply = f"### Analysis for {m['home_team']} vs {m['away_team']}\n"
                 if preds:
                     top = preds[0]
                     reply += f"- **Consensus Prediction:** H:{top['home_prob']:.2f} D:{top['draw_prob']:.2f} A:{top['away_prob']:.2f}\n- **Confidence:** {top.get('confidence', 0)*100:.1f}%"
                 else:
                     reply += "No AI predictions found for this match yet."
                 return { "available": True, "reply": reply, "thoughts": thoughts }

    # Default fallback
    return {
        "available": True,
        "reply": "I am the VIT Assistant, powered by native AI. I can provide:\n- **Market Intelligence** (SVI, Trends)\n- **System Health** (Agent status, model health)\n- **Sports Analysis** (Live odds, upcoming matches, deep insights)\n\nHow can I assist you today?",
        "thoughts": thoughts
    }

@router.post("/chat")
async def assistant_chat(body: ChatRequest, db: AsyncSession = Depends(get_db), _user=Depends(verify_api_key)):
    try:
        return await _handle_agentic_query(body.message, db)
    except Exception as e:
        logger.error(f"Assistant chat error: {e}", exc_info=True)
        return {
            "available": True,
            "reply": "I encountered an error while processing your request. Please try again later.",
            "thoughts": ["Error encountered"]
        }

@router.get("/status")
async def assistant_status(db: AsyncSession = Depends(get_db), _user=Depends(verify_api_key)):
    health = await _get_system_health_internal(db)
    return {
        "available": True,
        "backend_ai_available": True,
        "provider": "native",
        "message": "Assistant ready and operational.",
        "configured_providers": ["native"],
        "available_tools": [t["name"] for t in NATIVE_AI_TOOLS],
        "health": health
    }
