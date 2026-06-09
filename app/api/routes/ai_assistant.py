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

async def _call_gemini_agentic(
    message: str,
    history: Optional[List[dict]],
    context: Optional[str],
    db: AsyncSession
) -> Optional[Dict[str, Any]]:
    """
    Experimental Gemini 2.0 Flash Agentic Loop.
    Requires GEMINI_API_KEY.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        import httpx
        # Gemini API expects a specific format. This is a simplified version of tool-calling
        # using the REST API for Gemini 2.0 Flash.

        system_instructions = (
            "You are the VIT Network Intelligence Agent (v5.5.0). "
            "You have access to the VIT Network's internal tools and real-time data. "
            "Use these tools to provide accurate, data-driven answers about sports, "
            "market health (SVI), and system status. "
            "Always prefer internal data over general knowledge."
        )

        # In a real implementation, we would use the google-generativeai SDK.
        # Here we simulate the agentic behavior by allowing the LLM to 'request' tools
        # or we route based on its intent if we were using a shim.
        # For the purpose of this refactor, we will focus on the logic flow.

        # NOTE: Full tool-calling implementation usually requires a multi-turn conversation.
        # For now, we'll use a robust prompting strategy that encourages tool usage.

        return None # Placeholder for full SDK implementation
    except Exception as e:
        logger.warning(f"Gemini agentic call failed: {e}")
        return None

async def _handle_agentic_query(
    message: str,
    db: AsyncSession,
    history: Optional[List[dict]] = None,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    msg = message.lower()
    thoughts = ["Initiating VIT Intelligence Agent", "Accessing internal neural matrix"]

    # Try Gemini Agentic first if key exists
    # gemini_resp = await _call_gemini_agentic(message, history, context, db)
    # if gemini_resp: return gemini_resp

    # Enhanced Native Tool Dispatcher (Acting as the 'Agent' logic)

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
                # Add a few specific agent statuses if available
                active_agents = [a['name'] for a in agent_health['agents'] if a['status'] == 'ok']
                if active_agents:
                    reply += f"\n**Critical Systems:** {', '.join(active_agents[:4])} are online."

        return {"available": True, "reply": reply, "thoughts": thoughts}

    # 3. Sports Analysis (Integrated with Tool Map)
    if any(k in msg for k in ["match", "game", "soccer", "football", "prediction", "odds", "scores", "fixture"]):
        thoughts.append("Executing Sports Intelligence Toolset")

        # Try to find match ID first
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
                    # Use the first (usually highest weight) prediction
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

        # Otherwise show upcoming
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

    # 4. Fallback to LLM if possible, else structured Native Info
    thoughts.append("Generating response via language layer")
    api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")

    if api_key:
        # We reuse the _llm_chat logic but it would ideally be provider-agnostic
        # For now, we'll keep the existing call but refine the prompt if we had it
        llm_reply = await _llm_chat(message, history, context)
        if llm_reply:
            return {"available": True, "reply": llm_reply, "thoughts": thoughts}

    # 5. Ultimate Data-Rich Fallback (The "Native Assistant")
    health = await _get_system_health_internal(db)
    return {
        "available": True,
        "reply": (
            f"I am the VIT Intelligence Agent (v{health['system_version']}).\n\n"
            f"The network is currently **{health['status']}** with **{health['ai_models_ready']} active models**.\n"
            f"The Synthetic Value Index (SVI) is **{health['svi']:.4f}** ({health['svi_status']}).\n\n"
            f"How can I assist you with market intelligence, match insights, or system health today?"
        ),
        "thoughts": thoughts,
    }

async def _llm_chat(message: str, history: Optional[List[dict]], context: Optional[str]) -> Optional[str]:
    """Call OpenAI (or compatible) LLM if configured. Returns None if unavailable."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        import httpx
        system_prompt = (
            "You are the VIT Network Intelligence Agent — an expert embedded in the VIT Sports Analytics Network (v5.5.0). "
            "You help users understand match predictions, ML model outputs, market probabilities (SVI), "
            "and platform features. Use markdown for structure."
        )
        if context:
            system_prompt += f"\n\nContext:\n{context}"

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
                return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning(f"LLM call failed: {exc}")
    return None

@router.post("/chat")
async def assistant_chat(body: ChatRequest, db: AsyncSession = Depends(get_db), _user=Depends(verify_api_key)):
    try:
        return await _handle_agentic_query(body.message, db, history=body.history, context=body.context)
    except Exception as e:
        logger.error(f"Assistant chat error: {e}", exc_info=True)
        return {
            "available": True,
            "reply": "The VIT Intelligence Agent is temporarily unavailable. Please try again later.",
            "thoughts": ["Error encountered"],
        }

@router.get("/status")
async def assistant_status(db: AsyncSession = Depends(get_db), _user=Depends(verify_api_key)):
    health = await _get_system_health_internal(db)
    llm_configured = bool((os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY", "")).strip())
    return {
        "available": True,
        "backend_ai_available": True,
        "provider": "gemini" if os.getenv("GEMINI_API_KEY") else ("openai" if os.getenv("OPENAI_API_KEY") else "native"),
        "llm_configured": llm_configured,
        "message": f"VIT Intelligence Agent v{health['system_version']} ready.",
        "health": health,
    }
