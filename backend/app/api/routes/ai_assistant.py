from __future__ import annotations
import logging
import re
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.auth.dependencies import get_current_user, get_optional_user
from app.db.database import get_db
from app.core.dependencies import get_orchestrator
from app.db.models import Match
from app.db.repositories import MatchRepository
from app.services.assistant_tools import TOOL_MAP
from app.modules.ai.svi import SyntheticValueIndex
from app.services.ai_client import call_ai_with_provider, provider_status
from app.modules.assistant.service import AssistantConversationContext
from app.modules.platform.integration import platform_integration

router = APIRouter(prefix="/ai/assistant", tags=["ai-assistant"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None
    context: Optional[str] = None


class PlatformAssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Natural-language request or command for the shared AI platform")
    session_id: Optional[str] = Field(None, description="Conversation/session identifier used for assistant memory")
    workspace_id: Optional[str] = Field(None, description="Workspace scope for context and memory isolation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional caller-supplied context")
    execute: bool = Field(False, description="When true, return structured orchestration output instead of a JSON string reply")


class PlatformAssistantResponse(BaseModel):
    available: bool
    provider: str
    services: List[str]
    session_id: Optional[str]
    workspace_id: Optional[str]
    response: Any
    history: List[Dict[str, Any]]

async def _get_system_health_internal(db: AsyncSession) -> Dict[str, Any]:
    from sqlalchemy import select, func
    database_available = True
    try:
        match_count = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    except Exception as exc:
        logger.warning("Assistant database health query failed: %s", exc)
        match_count = None
        database_available = False

    try:
        orch = get_orchestrator()
        models_callable = orch.num_models_ready() if orch else 0
    except Exception as exc:
        logger.warning("Assistant model status query failed: %s", exc)
        models_callable = 0

    try:
        svi_report = await SyntheticValueIndex.get_market_health_report(db)
        svi_val = svi_report.get("svi")
        svi_status = svi_report.get("status", "unknown")
    except Exception as exc:
        logger.warning("Assistant SVI query failed: %s", exc)
        svi_val = None
        svi_status = "unavailable"

    return {
        "status": "available" if database_available else "degraded",
        "database_available": database_available,
        "matches_in_db": match_count,
        "ai_models_callable": models_callable,
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
    thoughts: list[str] = []

    live_data_groups = {
        "network telemetry": ("block", "gas", "chain", "hash", "consensus", "node", "validator", "ledger", "proof of storage"),
        "personal or financial data": ("wallet", "balance", "transaction", "transfer", "deposit", "withdraw", "paystack", "stripe", "credit", "debit", "convert"),
        "network policy": ("smart contract", "contract", "scholarship", "split", "reward"),
    }
    for data_group, terms in live_data_groups.items():
        if any(term in msg for term in terms):
            reply = (
                f"I can’t verify {data_group} from this assistant because no authorized live data source is connected "
                "to this chat. I won’t guess balances, transaction details, validator counts, chain status, or policy values. "
                "Please use the corresponding VIT Network application for current information."
            )
            return {
                "available": False,
                "data_status": "not_connected",
                "reply": reply,
                "response": reply,
                "thoughts": ["No authorized live source is available for this request."],
            }

    if any(k in msg for k in ["deactivated", "trouble", "fail", "broken", "offline", "degraded", "cache", "flush", "developer", "api key", "swagger", "route", "hot", "register"]):
        reply = (
            "I can offer general guidance, but I can’t verify current platform telemetry or perform administrative actions "
            "from this chat. Check the relevant VIT Network status or administration screen for live state."
        )
        return {
            "available": False,
            "data_status": "not_connected",
            "reply": reply,
            "response": reply,
            "thoughts": ["Live operations and administrative actions are not connected to this chat."],
        }

    # 1. Blockchain Data & Telemetry
    if any(k in msg for k in ["block", "gas", "chain", "hash", "consensus", "node", "validator", "ledger", "proof of storage"]):
        thoughts.append("Querying Blockchain Ledger Diagnostics & Validator Telemetry")
        try:
            reply = (
                "### VIT L2 Blockchain Diagnostics\n\n"
                "- **Chain ID:** `7764` (Base-anchored L2 rollup)\n"
                "- **Block Time Target:** `15.0 seconds`\n"
                "- **Consensus Protocol:** Proof of Storage (PoS) + Verifiable Oracle Results\n"
                "- **Gas Metric Average:** `21 Gwei`\n"
                "- **Active Validators:** `8 nodes` currently registered in the epoch\n\n"
                "**Consensus Status:** 100% synchronized. Block height validated at root. "
                "Storage challenges are scheduled and dispatched dynamically every epoch."
            )
            return {"available": True, "reply": reply, "response": reply, "thoughts": thoughts}
        except Exception as e:
            logger.error(f"Blockchain telemetry check failed: {e}")

    # 2. Wallet Transactions & Financial Rails
    if any(k in msg for k in ["wallet", "transaction", "paystack", "stripe", "transfer", "balance", "credit", "debit", "deposit", "convert"]):
        thoughts.append("Auditing Payment Rails and Wallet balances")
        try:
            reply = (
                "### VIT Financial Rails & Ledger\n\n"
                "- **Supported Liquidity Rails:** Paystack (NGN, USD), Stripe (USDT, USD), On-Chain (VIT, USDT)\n"
                "- **Wallet Idempotency Status:** Enabled. All mutate requests enforce `X-Idempotency-Key` headers.\n"
                "- **Balance Engine State:** Active. Ledgers require immediate matching within `async with db.begin()` scopes.\n"
                "- **Ecosystem Pricing Engine:** Native VITCoin hybrid formula is online.\n\n"
                "**Audit Note:** Financial settlements are fully secured, and double-spend attempts are dynamically caught at the db constraints level."
            )
            return {"available": True, "reply": reply, "response": reply, "thoughts": thoughts}
        except Exception as e:
            logger.error(f"Wallet telemetry check failed: {e}")

    # 3. Smart Contracts & Splitting Logic
    if any(k in msg for k in ["smart contract", "contract", "split", "scholarship", "split ratio"]):
        thoughts.append("Evaluating Smart Contract splits and reward distributions")
        try:
            reply = (
                "### VIT Smart Contract reward distribution\n\n"
                "- **Reward Split Target**: 70% to local Node Operator, 30% to University Scholarship Pool\n"
                "- **Canonical scholarship pool username**: `university_scholarship_pool`\n"
                "- **Splitting Rule Engine**: Idempotent database-secured transactions.\n\n"
                "**Rule Audit**: Standard splits occur automatically at the moment of match result settlement."
            )
            return {"available": True, "reply": reply, "response": reply, "thoughts": thoughts}
        except Exception as e:
            logger.error(f"Contract splitting check failed: {e}")

    # 4. Platform Troubleshooting
    if any(k in msg for k in ["deactivated", "trouble", "fail", "broken", "offline", "degraded", "cache", "flush"]):
        thoughts.append("Processing platform troubleshooting and telemetry")
        try:
            reply = (
                "### VIT Platform Troubleshooting Guide\n\n"
                "- **User Account issues**: If a user is flagged inactive or deactivated, verify if they have triggered any security flags inside the `FraudFlag` table.\n"
                "- **Cache issues**: To resolve stale metrics or missing live blocks, clear the Redis Cache using `POST /api/ai-engine/weights/sync` or from the Admin Center.\n"
                "- **Database pool timeouts**: If the database is marked degraded, check for open connection leaks in sub-routers or non-async ORM commands (ensure all DB commands are async-awaited).\n\n"
                "If you need manual intervention, check the logs or request the operator to trigger a provider restart."
            )
            return {"available": True, "reply": reply, "response": reply, "thoughts": thoughts}
        except Exception as e:
            logger.error(f"Troubleshooting assist failed: {e}")

    # 5. Admin & Developer Assistant
    if any(k in msg for k in ["developer", "api key", "swagger", "route", "hot", "register"]):
        thoughts.append("Accessing Admin & Developer API guidelines")
        try:
            reply = (
                "### Admin & Developer Assistant\n\n"
                "- **API Key Authentication**: Exposes `X-API-Key` headers for third-party microservice integration.\n"
                "- **Model Hot Registration**: Can register any new predictive model on-the-fly via `POST /api/ai-engine/models/register`.\n"
                "- **Documentation Endpoints**: Swaggers are mounted directly under `/docs` and fallback directly onto standard React SPA.\n\n"
                "Check `/api/ai-engine/status` for live orchestrator and directory pathways."
            )
            return {"available": True, "reply": reply, "response": reply, "thoughts": thoughts}
        except Exception as e:
            logger.error(f"Developer helper check failed: {e}")

    # 1. Market Intelligence & SVI
    if any(k in msg for k in ["svi", "market health", "collateral", "inflation", "trends", "clv"]):
        thoughts.append("Querying Synthetic Value Index & Market Trends")
        try:
            svi_report = await SyntheticValueIndex.get_market_health_report(db)
            svi_value = svi_report.get("svi")
            svi_display = f"{svi_value:.4f}" if isinstance(svi_value, (int, float)) else "Unavailable"
            reply = (
                f"### VIT Market Intelligence\n\n"
                f"**Synthetic Value Index (SVI):** {svi_display} ({svi_report.get('status', 'unknown')})\n"
                "**Source:** Current SVI database report. Order-book and live market signals are not connected here.\n"
            )

            if "get_market_trends" in TOOL_MAP:
                trends = await TOOL_MAP["get_market_trends"]()
                if trends and trends.get("total_bets", 0) > 0 and "overall_avg_clv" in trends:
                    reply += f"\n**Network CLV:** {trends['overall_avg_clv']:.4f} | **Tracked Events:** {trends['total_bets']}"

            return {"available": True, "reply": reply, "response": reply, "thoughts": thoughts}
        except Exception as e:
            logger.error(f"SVI tool error: {e}")
            reply = "Market intelligence engine is re-calibrating. Please try again in a moment."
            return {"available": True, "reply": reply, "response": reply, "thoughts": thoughts}

    # 1.5 Accuracy & Performance
    if any(k in msg for k in ["accuracy", "performance", "track record", "success rate", "correct"]):
        thoughts.append("Querying verified prediction evaluation metrics")
        try:
            from app.services.prediction_evaluation_service import PredictionEvaluationService
            metrics = await PredictionEvaluationService.get_performance_analytics(db=db, exclude_demo=True)
            sample_size = metrics.get("sample_size", 0)
            if sample_size:
                reply = (
                    "### Verified Prediction Evaluation\n\n"
                    f"- **Evaluated predictions:** {sample_size}\n"
                    f"- **Outcome accuracy:** {metrics['overall_accuracy']:.1%}\n"
                    f"- **Mean multiclass Brier score:** {metrics['mean_brier_score']:.4f} (lower is better)\n"
                    f"- **Mean log loss:** {metrics['mean_log_loss']:.4f} (lower is better)\n\n"
                    f"{metrics.get('disclaimer', '')}"
                )
            else:
                reply = (
                    "No verified, non-demo evaluated predictions are available for this report. "
                    "Accuracy is not reported until predictions are evaluated against verified outcomes."
                )
            return {"available": True, "data_status": "verified_evaluation", "reply": reply, "response": reply, "thoughts": thoughts}
        except Exception as e:
            logger.error(f"Accuracy tool error: {e}")

    # 2. System Health & Agent Status
    if any(k in msg for k in ["health", "status", "ready", "models", "agents", "guardian"]):
        thoughts.append("Auditing VIT Agent Network")
        health = await _get_system_health_internal(db)
        svi = health.get("svi")
        svi_display = f"{svi:.4f}" if isinstance(svi, (int, float)) else "Unavailable"
        matches = health.get("matches_in_db")
        matches_display = str(matches) if matches is not None else "Unavailable"
        db_status = "available" if health.get("database_available") else "unavailable"
        reply = (
            f"### VIT Network Status: {health['status'].upper()}\n"
            f"- **Database:** {db_status}\n"
            f"- **Matches indexed:** {matches_display}\n"
            f"- **Local model wrappers callable:** {health['ai_models_callable']} (this does not mean trained weights are loaded)\n"
            f"- **SVI:** {svi_display} ({health['svi_status']})\n"
        )

        if "get_system_health" in TOOL_MAP:
            agent_health = await TOOL_MAP["get_system_health"]()
            if agent_health and "agents" in agent_health:
                reply += f"- **Reported agents:** {len(agent_health['agents'])}\n"
                active_agents = [a['name'] for a in agent_health['agents'] if a['status'] == 'ok']
                if active_agents:
                    reply += f"\n**Agents reporting OK:** {', '.join(active_agents[:4])}."

        return {"available": health["database_available"], "data_status": health["status"], "reply": reply, "response": reply, "thoughts": thoughts}

    # 3. Sports Analysis & Predictions
    if any(k in msg for k in ["match", "game", "soccer", "football", "basketball", "tennis", "prediction", "confidence", "odds", "scores", "fixture", "highest", "today"]):
        thoughts.append("Executing Sports Intelligence Toolset")

        is_highest = any(k in msg for k in ["highest", "top", "best", "most confident"])
        is_today = "today" in msg
        is_prediction_query = any(k in msg for k in ["prediction", "confidence", "highest", "best", "top", "explain"])

        sport_filter = None
        if "football" in msg or "soccer" in msg:
            sport_filter = "football"
        elif "basketball" in msg:
            sport_filter = "basketball"
        elif "tennis" in msg:
            sport_filter = "tennis"

        if is_today or is_highest or (is_prediction_query and any(k in msg for k in ["match", "game", "fixture", "show", "list", "prediction", "explain"])):
            thoughts.append("Querying database for matches & predictions")
            try:
                from sqlalchemy import select, desc
                from datetime import datetime, timezone, timedelta
                from app.db.models import Match, Prediction

                now_utc = datetime.now(timezone.utc)
                start_of_day = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(days=1)

                query = select(Match, Prediction).join(Prediction, Match.id == Prediction.match_id, isouter=True)

                if is_today:
                    query = query.where(Match.kickoff_time >= start_of_day.replace(tzinfo=None), Match.kickoff_time < end_of_day.replace(tzinfo=None))
                else:
                    query = query.where(Match.kickoff_time >= now_utc.replace(tzinfo=None) - timedelta(hours=6))

                if sport_filter:
                    query = query.where(Match.sport.ilike(f"%{sport_filter}%"))

                query = query.order_by(desc(Prediction.confidence), Match.kickoff_time.asc()).limit(10)

                result = await db.execute(query)
                rows = result.all()

                if rows:
                    lines = []
                    for idx, (m, p) in enumerate(rows, 1):
                        sport_str = (m.sport or "sports").capitalize()
                        league_str = m.league or "Unknown League"
                        kickoff_str = m.kickoff_time.strftime("%Y-%m-%d %H:%M UTC") if m.kickoff_time else "TBD"

                        conf_pct = f"{round(p.confidence * 100, 1)}%" if (p and p.confidence is not None) else "N/A"

                        pred_desc = "Pending calculation"
                        if p:
                            if p.bet_side:
                                pred_desc = p.bet_side.capitalize()
                            elif p.home_prob >= p.draw_prob and p.home_prob >= p.away_prob:
                                pred_desc = f"Home Win ({m.home_team})"
                            elif p.away_prob >= p.home_prob and p.away_prob >= p.draw_prob:
                                pred_desc = f"Away Win ({m.away_team})"
                            else:
                                pred_desc = "Draw"

                        lines.append(
                            f"{idx}. **{m.home_team} vs {m.away_team}**\n" +
                            f"   - **Sport:** {sport_str} ({league_str})\n" +
                            f"   - **Kickoff:** {kickoff_str}\n" +
                            f"   - **Prediction:** {pred_desc}\n" +
                            f"   - **AI Confidence:** {conf_pct}"
                        )

                    header_title = "Highest AI Confidence Matches" if is_highest else "Matches & AI Predictions"
                    if is_today:
                        header_title += " Today"
                    if sport_filter:
                        header_title += f" ({sport_filter.capitalize()})"

                    reply = f"### {header_title}\n\n" + "\n\n".join(lines)
                    return {"available": True, "data_status": "database_records", "reply": reply, "response": reply, "thoughts": thoughts}
                else:
                    sport_suffix = f" for {sport_filter.capitalize()}" if sport_filter else ""
                    reply = f"I couldn't find any scheduled matches or recorded forecasts{sport_suffix} in the requested time range."
                    return {"available": True, "data_status": "no_records", "reply": reply, "response": reply, "thoughts": thoughts}

            except Exception as e:
                logger.error(f"Error fetching predictions for assistant query: {e}", exc_info=True)
                reply = "I encountered an error retrieving predictions from the database."
                return {"available": False, "data_status": "query_failed", "reply": reply, "response": reply, "thoughts": thoughts}

        match_id_search = re.search(r"(?:id\s*[:#]?\s*|match\s+)(\d+)", msg)
        found_matches = []
        if match_id_search:
            match_id = int(match_id_search.group(1))
            insights = await TOOL_MAP["get_match_insights"](match_id)
            if "error" not in insights:
                found_matches.append(insights)
        else:
            match_repo = MatchRepository(db)
            words = [w for w in msg.split() if len(w) > 3 and w not in ["match", "game", "soccer", "football", "prediction", "odds", "scores", "fixture", "insight"]]
            if words:
                search_term = words[0]
                matches = await match_repo.search_by_team(search_term, limit=3)
                for m in matches:
                    insights = await TOOL_MAP["get_match_insights"](m.id)
                    if "error" not in insights:
                        found_matches.append(insights)

        if found_matches:
            reply = ""
            for insights in found_matches:
                m = insights["match"]
                preds = insights["predictions"]
                reply += f"### Tactical Insight: {m.get('home_team', 'Unknown')} vs {m.get('away_team', 'Unknown')}\n"
                reply += f"*League: {m.get('league', 'Unknown')} | Kickoff: {m.get('kickoff_time', 'Unknown')}*\n\n"
                if preds:
                    p = preds[0]
                    reply += f"**Recorded forecast ({p.get('source') or 'source unknown'}):**\n"
                    reply += f"- Home Win: {p.get('home_prob', 0)*100:.1f}%\n"
                    reply += f"- Draw: {p.get('draw_prob', 0)*100:.1f}%\n"
                    reply += f"- Away Win: {p.get('away_prob', 0)*100:.1f}%\n"
                    confidence = p.get("confidence")
                    confidence_display = f"{confidence * 100:.1f}%" if isinstance(confidence, (int, float)) else "Not reported"
                    reply += f"- **Reported confidence (not accuracy):** {confidence_display}\n\n"
                else:
                    reply += "No forecast is recorded for this match.\n\n"
            return {"available": True, "data_status": "database_records", "reply": reply.strip(), "response": reply.strip(), "thoughts": thoughts}

        upcoming = await TOOL_MAP["get_upcoming_matches"](limit=5)
        if upcoming:
            match_list = "\n".join([
                f"- **{m.get('home_team', 'Unknown')} vs {m.get('away_team', 'Unknown')}** (ID: {m.get('id', 'Unknown')}) | {m.get('league', 'Unknown')}"
                for m in upcoming
            ])
            reply = (
                f"### Upcoming Network Fixtures\n"
                f"I found the following matches in the VIT database:\n\n{match_list}\n\n"
                f"Ask me for 'insight on match [ID]' for a deep dive analysis."
            )
            return {"available": True, "reply": reply, "response": reply, "thoughts": thoughts}

    # 4. Native Natural Language Generation
    thoughts.append("Generating response via VIT Native NLP layer")
    health = await _get_system_health_internal(db)

    ctx = {
        "health": health,
        "accuracy": None,
        "evidence_note": "Only values in this context are verified live data; do not invent missing network state or prediction results.",
    }
    reply, provider = await call_ai_with_provider(message, context=ctx)
    available = provider != "unavailable"
    return {
        "available": available,
        "provider": provider,
        "data_status": "not_connected" if not available else "generated_response",
        "reply": reply,
        "response": reply,
        "thoughts": thoughts,
    }

def _platform_context(body: PlatformAssistantRequest, user: Any) -> AssistantConversationContext:
    role = getattr(user, "role", None)
    roles = [role] if role else []
    return AssistantConversationContext(
        user_id=str(user.id),
        session_id=body.session_id,
        workspace_id=body.workspace_id,
        roles=roles,
        metadata=body.metadata,
    )


@router.post(
    "/platform/chat",
    response_model=PlatformAssistantResponse,
    summary="Chat with the shared AI platform assistant",
    description=(
        "Runs the global assistant as a platform orchestration layer over the "
        "existing command palette, event bus, search platform, notification "
        "platform, identity service, and gateway-mounted AI route."
    ),
)
async def platform_assistant_chat(body: PlatformAssistantRequest, current_user=Depends(get_current_user)):
    context = _platform_context(body, current_user)
    if body.execute:
        response: Any = await platform_integration.assistant.execute(body.message, context)
    else:
        response = await platform_integration.assistant.ask(body.message, context)
    return PlatformAssistantResponse(
        available=True,
        provider="platform",
        services=platform_integration.assistant.registered_services(),
        session_id=context.session_id,
        workspace_id=context.workspace_id,
        response=response,
        history=platform_integration.assistant.get_history(context),
    )


@router.get(
    "/platform/history",
    summary="Get shared AI platform assistant conversation history",
    description="Returns the in-process memory for the authenticated user/session/workspace scope.",
)
async def platform_assistant_history(
    session_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    context = AssistantConversationContext(
        user_id=str(current_user.id),
        session_id=session_id,
        workspace_id=workspace_id,
        roles=[getattr(current_user, "role", "user")],
    )
    return {
        "available": True,
        "provider": "platform",
        "session_id": session_id,
        "workspace_id": workspace_id,
        "history": platform_integration.assistant.get_history(context),
    }


@router.get(
    "/platform/status",
    summary="Get shared AI platform assistant integration status",
    description="Reports which platform services are wired into the global assistant.",
)
async def platform_assistant_status(_current_user=Depends(get_current_user)):
    services = platform_integration.assistant.registered_services()
    required = {"identity", "events", "search", "notifications", "commands"}
    return {
        "available": required.issubset(set(services)),
        "provider": "platform",
        "services": services,
        "required_services": sorted(required),
        "gateway_route": "/api/ai/assistant/platform/chat",
    }


@router.post("/chat")
async def assistant_chat(body: ChatRequest, db: AsyncSession = Depends(get_db), _user=Depends(get_optional_user)):
    try:
        return await _handle_agentic_query(body.message, db, history=body.history, context=body.context)
    except Exception as e:
        logger.error(f"Assistant chat error: {e}", exc_info=True)
        return {
            "available": False,
            "data_status": "error",
            "reply": "The VIT AI Assistant is temporarily unavailable. Please try again later.",
            "response": "The VIT AI Assistant is temporarily unavailable. Please try again later.",
            "thoughts": ["Error encountered"],
        }

@router.get("/status")
async def assistant_status(db: AsyncSession = Depends(get_db), _user=Depends(get_optional_user)):
    health = await _get_system_health_internal(db)
    providers = await provider_status()
    try:
        from app.services.vit_ai_client import vit_ai_client
        vit_ai_available = await vit_ai_client.check_health()
    except Exception as exc:
        logger.warning("VIT AI upstream health check failed: %s", exc)
        vit_ai_available = False

    external_configured = any(
        bool(providers.get(name, {}).get("configured"))
        for name in ("gemini", "aimlapi")
    )
    assistant_status = (
        "available" if vit_ai_available
        else "configured_but_unverified" if external_configured
        else "unavailable"
    )
    return {
        "available": vit_ai_available,
        "status": assistant_status,
        "backend_ai_available": health["database_available"],
        "provider": "vit-ai" if vit_ai_available else None,
        "llm_configured": bool(vit_ai_available or external_configured),
        "providers": providers,
        "message": (
            f"VIT AI Assistant v{health['system_version']} is available."
            if vit_ai_available
            else "No conversational AI provider has verified availability; configured external providers are not probed here."
        ),
        "health": health,
    }
