from __future__ import annotations
import logging
import asyncio
import os
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
        "system_version": "5.5.0"
    }


async def _llm_chat(message: str, history: Optional[List[dict]], context: Optional[str]) -> Optional[str]:
    """Call OpenAI (or compatible) LLM if configured. Returns None if unavailable."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        import httpx

        system_prompt = (
            "You are the VIT Network AI Assistant — an expert sports intelligence system "
            "embedded in the VIT Sports Analytics Network (v5.5.0). "
            "You help users understand match predictions, ML model outputs, market probabilities, "
            "betting concepts (Kelly criterion, CLV, vig-free odds), and platform features. "
            "Be concise, data-driven, and helpful. Use markdown for structure when it aids clarity."
        )
        if context:
            system_prompt += f"\n\nAdditional context:\n{context}"

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for h in history[-6:]:
                role = h.get("role", "user")
                content = h.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": messages,
                    "max_tokens": 800,
                    "temperature": 0.4,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning(f"LLM call failed: {exc}")
    return None


async def _handle_agentic_query(
    message: str,
    db: AsyncSession,
    history: Optional[List[dict]] = None,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    msg = message.lower()
    thoughts = ["Analyzing intent", "Scanning system context"]

    # 1. Market Intelligence / SVI Queries
    if any(k in msg for k in ["svi", "market health", "collateral", "inflation", "trends", "clv"]):
        thoughts.append("Fetching Synthetic Value Index and Market Trends")
        try:
            from exchange.order_book import OrderBook
            report = await AICopilot.get_market_copilot_report(db, OrderBook(), [], {}, {})
            trends = {}
            if "get_market_trends" in TOOL_MAP:
                trends = await TOOL_MAP["get_market_trends"]()
            insights = "\n".join([f"- {i}" for i in report["insights"]])
            reply = f"### Market Intelligence Report\n\n{insights}\n\n**SVI Status:** {report['svi'].get('status', 'healthy')}\n"
            if trends and "overall_avg_clv" in trends:
                reply += f"**Overall Avg CLV:** {trends['overall_avg_clv']:.4f}\n**Total Bets Tracked:** {trends['total_bets']}"
        except Exception:
            reply = "Market intelligence data is currently unavailable. Please check that the exchange module is configured."
        return {"available": True, "reply": reply, "thoughts": thoughts}

    # 2. System Health / Status
    if any(k in msg for k in ["health", "status", "ready", "models", "agents"]):
        thoughts.append("Querying system health and agent status")
        health = await _get_system_health_internal(db)
        agent_health = {}
        if "get_system_health" in TOOL_MAP:
            agent_health = await TOOL_MAP["get_system_health"]()
        reply = (
            f"### System Status: {health['status'].upper()}\n"
            f"- **Version:** {health['system_version']}\n"
            f"- **AI Models:** {health['ai_models_ready']} active\n"
            f"- **Total Matches:** {health['matches_in_db']}\n"
        )
        if agent_health and "agents" in agent_health:
            reply += f"- **Active Agents:** {len(agent_health['agents'])}\n"
        return {"available": True, "reply": reply, "thoughts": thoughts}

    # 3. Sports Analysis & Odds
    if any(k in msg for k in ["match", "game", "soccer", "football", "prediction", "odds", "scores", "fixture"]):
        thoughts.append("Processing sports data request")
        if "odds" in msg and "get_live_odds" in TOOL_MAP:
            try:
                odds_data = await TOOL_MAP["get_live_odds"]("premier_league")
                if "odds" in odds_data and odds_data["odds"]:
                    m = odds_data["odds"][0]
                    return {
                        "available": True,
                        "reply": (
                            f"I found live odds for **{m['home_team']} vs {m['away_team']}**:\n"
                            f"- Home: {m['home_odds']}\n- Draw: {m['draw_odds']}\n- Away: {m['away_odds']}\n"
                            f"(Source: {m['bookmaker']})"
                        ),
                        "thoughts": thoughts,
                    }
            except Exception:
                pass

        from sqlalchemy import select
        from datetime import datetime
        result = await db.execute(
            select(Match)
            .where(Match.kickoff_time > datetime.utcnow())
            .order_by(Match.kickoff_time)
            .limit(5)
        )
        matches = result.scalars().all()
        if matches:
            match_list = "\n".join([
                f"- **{m.home_team} vs {m.away_team}** — {m.kickoff_time.strftime('%d %b %Y %H:%M')} UTC  (league: {m.league or 'unknown'})"
                for m in matches
            ])
            # Try to enrich with LLM analysis if available
            llm_context = f"Upcoming matches:\n{match_list}"
            llm_reply = await _llm_chat(message, history, llm_context)
            if llm_reply:
                return {"available": True, "reply": llm_reply, "thoughts": thoughts + ["LLM enrichment applied"]}
            return {
                "available": True,
                "reply": f"Here are the next upcoming matches in the VIT database:\n\n{match_list}\n\nAsk for insights using a match ID.",
                "thoughts": thoughts,
            }

    # 4. Specific Match Insight
    if "insight" in msg or "analyze" in msg or "analys" in msg:
        import re
        match_id_search = re.search(r'(?:id\s*[:#]?\s*|match\s+)(\d+)', msg)
        if match_id_search and "get_match_insights" in TOOL_MAP:
            match_id = int(match_id_search.group(1))
            thoughts.append(f"Fetching deep insights for match {match_id}")
            try:
                insights = await TOOL_MAP["get_match_insights"](match_id)
                if "error" not in insights:
                    m = insights["match"]
                    preds = insights["predictions"]
                    reply = f"### Analysis for {m['home_team']} vs {m['away_team']}\n"
                    if preds:
                        top = preds[0]
                        reply += (
                            f"- **Consensus:** H:{top['home_prob']:.2f} / D:{top['draw_prob']:.2f} / A:{top['away_prob']:.2f}\n"
                            f"- **Confidence:** {top.get('confidence', 0)*100:.1f}%"
                        )
                    else:
                        reply += "No AI predictions found for this match yet."
                    return {"available": True, "reply": reply, "thoughts": thoughts}
            except Exception:
                pass

    # 5. Fall through to LLM if OpenAI is configured
    thoughts.append("Routing to language model")
    llm_reply = await _llm_chat(message, history, context)
    if llm_reply:
        return {"available": True, "reply": llm_reply, "thoughts": thoughts}

    # 6. Native fallback when no LLM is configured
    return {
        "available": True,
        "reply": (
            "I am the VIT Assistant, powered by native AI. I can help with:\n"
            "- **Market Intelligence** — SVI, CLV trends, collateral analysis\n"
            "- **System Health** — agent status, model readiness\n"
            "- **Sports Analysis** — upcoming fixtures, live odds, deep match insights\n\n"
            "For open-ended questions, set `OPENAI_API_KEY` to enable full LLM responses.\n\n"
            "How can I assist you today?"
        ),
        "thoughts": thoughts,
    }


@router.post("/chat")
async def assistant_chat(body: ChatRequest, db: AsyncSession = Depends(get_db), _user=Depends(verify_api_key)):
    try:
        return await _handle_agentic_query(body.message, db, history=body.history, context=body.context)
    except Exception as e:
        logger.error(f"Assistant chat error: {e}", exc_info=True)
        return {
            "available": True,
            "reply": "I encountered an error while processing your request. Please try again.",
            "thoughts": ["Error encountered"],
        }


@router.get("/status")
async def assistant_status(db: AsyncSession = Depends(get_db), _user=Depends(verify_api_key)):
    health = await _get_system_health_internal(db)
    llm_configured = bool(os.getenv("OPENAI_API_KEY", "").strip())
    return {
        "available": True,
        "backend_ai_available": True,
        "provider": "openai" if llm_configured else "native",
        "llm_configured": llm_configured,
        "message": "Assistant ready and operational." + (" LLM active." if llm_configured else " Set OPENAI_API_KEY for full LLM responses."),
        "configured_providers": ["openai", "native"] if llm_configured else ["native"],
        "available_tools": [t["name"] for t in NATIVE_AI_TOOLS],
        "health": health,
    }
