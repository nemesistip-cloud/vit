"""app/services/gemini_chat.py — Multi-provider AI chat with Gemini→Claude→Grok→SCIE cascade."""

import logging
import os
import re
from typing import List, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


def _scie_fallback_reply(message: str, context: Optional[str]) -> str:
    """Generate a statistically-grounded reply when all LLM providers are unavailable.

    Parses match context (if present) and builds a structured response using
    the SCIE engine. Falls back to a general platform guide for non-match queries.
    """
    msg_lower = message.lower()

    # ── Parse match context if provided ──────────────────────────────────────
    home_team = away_team = league = None
    home_prob = draw_prob = away_prob = None
    over_25_prob = btts_prob = confidence = None
    bet_side = entry_odds = edge = None

    if context:
        _team_match = re.search(r"Fixture:\s*(.+?)\s+vs\s+(.+)", context, re.IGNORECASE)
        if _team_match:
            home_team = _team_match.group(1).strip()
            away_team = _team_match.group(2).strip()
        _league = re.search(r"League:\s*(.+)", context)
        if _league:
            league = _league.group(1).strip()
        _hprob = re.search(r"Home win:\s*([\d.]+)%", context)
        _dprob = re.search(r"Draw:\s*([\d.]+)%", context)
        _aprob = re.search(r"Away win:\s*([\d.]+)%", context)
        if _hprob:
            home_prob = float(_hprob.group(1)) / 100
        if _dprob:
            draw_prob = float(_dprob.group(1)) / 100
        if _aprob:
            away_prob = float(_aprob.group(1)) / 100
        _over = re.search(r"Over 2\.5:\s*([\d.]+)%", context)
        _btts = re.search(r"BTTS Yes:\s*([\d.]+)%", context)
        _conf = re.search(r"Model confidence:\s*([\d.]+)%", context)
        _side = re.search(r"Side:\s*(\w+)", context)
        _odds = re.search(r"Odds:\s*([\d.]+)", context)
        _edge = re.search(r"Edge:\s*([-\d.]+)%", context)
        if _over:
            over_25_prob = float(_over.group(1)) / 100
        if _btts:
            btts_prob = float(_btts.group(1)) / 100
        if _conf:
            confidence = float(_conf.group(1)) / 100
        if _side:
            bet_side = _side.group(1)
        if _odds:
            entry_odds = float(_odds.group(1))
        if _edge:
            edge = float(_edge.group(1)) / 100

    # ── Match-specific query with probabilities ───────────────────────────────
    if home_team and home_prob is not None:
        from app.services.deterministic_insights import generate_deterministic_insights
        insight = generate_deterministic_insights(
            home_team=home_team,
            away_team=away_team or "Away",
            league=league or "default",
            home_prob=home_prob,
            draw_prob=draw_prob or 0.26,
            away_prob=away_prob or (1 - home_prob - (draw_prob or 0.26)),
            over_25_prob=over_25_prob,
            btts_prob=btts_prob,
            bet_side=bet_side,
            edge=edge or 0.0,
            entry_odds=entry_odds,
            confidence=confidence or 0.5,
        )
        hp = insight["home_prob"]
        dp = insight["draw_prob"]
        ap = insight["away_prob"]
        top_side = "Home Win" if hp >= max(dp, ap) else ("Draw" if dp >= ap else "Away Win")
        top_prob = max(hp, dp, ap)

        # Build a contextual response based on what the user asked
        if any(k in msg_lower for k in ["risk", "danger", "concern", "worry"]):
            reply = (
                f"**Key risks for {home_team} vs {away_team}**\n\n"
                f"The 13-model ensemble rates this as a **{insight['risk_level']} risk** fixture:\n\n"
            )
            for factor in insight["key_factors"]:
                reply += f"- {factor}\n"
            reply += (
                f"\n**Value assessment:** {insight['value_assessment']}\n\n"
                f"Entropy across the 1X2 market is {'high — models disagree' if top_prob < 0.50 else 'moderate — lean toward ' + top_side}. "
                f"{'BTTS elevated at ' + str(round(btts_prob*100)) + '%' if btts_prob and btts_prob >= 0.55 else ''}"
                f"\n\n*Powered by VIT Statistical Engine — add a GEMINI_API_KEY for deeper LLM analysis.*"
            )
        elif any(k in msg_lower for k in ["value", "bet", "stake", "wager", "back", "lay"]):
            reply = (
                f"**{home_team} vs {away_team} — Betting Analysis**\n\n"
                f"{insight['recommendation']}\n\n"
                f"**Model breakdown:**\n"
                f"- Home: {hp*100:.1f}% | Draw: {dp*100:.1f}% | Away: {ap*100:.1f}%\n"
                f"- Recommended side: {bet_side or top_side} @ {entry_odds or 'N/A'}\n"
                f"- Edge: {(edge or 0)*100:.2f}% {'(value bet)' if edge and edge > 0.03 else ''}\n\n"
                f"{insight['value_assessment']}"
                f"\n\n*Powered by VIT Statistical Engine — add a GEMINI_API_KEY for LLM-powered analysis.*"
            )
        elif any(k in msg_lower for k in ["over", "under", "goal", "btts", "both"]):
            if over_25_prob is not None:
                direction = "**Over 2.5** (lean)" if over_25_prob >= 0.55 else ("**Under 2.5** (lean)" if over_25_prob <= 0.42 else "**Neutral** — no strong edge")
                reply = (
                    f"**Goals market — {home_team} vs {away_team}**\n\n"
                    f"Over 2.5 probability: **{over_25_prob*100:.1f}%** → {direction}\n"
                    f"{'BTTS Yes: **' + str(round(btts_prob*100)) + '%**' if btts_prob else ''}\n\n"
                    f"The ensemble signals {direction} based on league-specific goal rates "
                    f"and team attacking/defensive patterns."
                    f"\n\n*Powered by VIT Statistical Engine.*"
                )
            else:
                reply = f"Over/Under data not available for this fixture. The home win probability is {hp*100:.1f}%."
        elif any(k in msg_lower for k in ["favor", "favourite", "favorite", "why", "reason", "explain"]):
            reply = (
                f"**Why the model favours {top_side} ({top_prob*100:.1f}%)**\n\n"
                f"{insight['summary']}\n\n"
                f"**Key factors:**\n"
            )
            for factor in insight["key_factors"]:
                reply += f"- {factor}\n"
            reply += f"\n*Powered by VIT Statistical Engine.*"
        else:
            reply = (
                f"**{home_team} vs {away_team} — Statistical Summary**\n\n"
                f"{insight['summary']}\n\n"
                f"**Recommendation:** {insight['recommendation']}\n"
                f"**Risk level:** {insight['risk_level']}\n\n"
                f"*Powered by VIT Statistical Engine — no LLM API key required.*"
            )
        return reply

    # ── General platform queries ───────────────────────────────────────────────
    if any(k in msg_lower for k in ["vitcoin", "wallet", "deposit", "withdraw", "balance"]):
        return (
            "**VITCoin Wallet**\n\n"
            "Your VITCoin wallet is accessible at `/wallet`. Deposit via Stripe (USD), Paystack (NGN), "
            "or USDT. 1 VIT is auto-minted per $1 USD deposited.\n\n"
            "- View balance, transactions, and exchange rates on the Wallet page.\n"
            "- Withdrawals require KYC verification.\n"
            "- VITCoin is used for marketplace model calls, staking, and governance votes.\n\n"
            "*Add GEMINI_API_KEY for conversational AI responses.*"
        )
    if any(k in msg_lower for k in ["prediction", "model", "accuracy", "ensemble"]):
        return (
            "**13-Model Ensemble Predictions**\n\n"
            "VIT uses a 13-model ML ensemble including XGBoost, LightGBM, Random Forest, "
            "Neural Networks, and Poisson regression, calibrated per-league.\n\n"
            "- Predictions show 1X2, Over/Under 2.5, and BTTS probabilities.\n"
            "- Confidence scores are temperature-scaled via proper scoring rules.\n"
            "- Model weights are updated every 6 hours via RL reward signals.\n"
            "- The Statistical Engine (SCIE) provides baseline priors when AI is offline.\n\n"
            "*Add GEMINI_API_KEY for AI-powered analysis on any match.*"
        )
    if any(k in msg_lower for k in ["chain", "blockchain", "ledger", "stake"]):
        return (
            "**VIT-Chain Sovereign Ledger**\n\n"
            "VIT-Chain is a hash-linked SQLite ledger with PoW difficulty=4. It records:\n\n"
            "- VITCoin minting and transfers\n"
            "- Validator consensus votes\n"
            "- Prediction settlement\n\n"
            "Explore at `/api/chain/stats`. Staking earns 5% revenue share from model calls."
            "\n\n*Add GEMINI_API_KEY for AI-powered responses.*"
        )

    # Generic fallback
    return (
        "I'm running in **Statistical Mode** (no LLM API key configured). "
        "I can answer questions about match probabilities, goals markets, betting value, "
        "model predictions, VITCoin, and platform features.\n\n"
        "For richer AI responses, add `GEMINI_API_KEY`, `CLAUDE_API_KEY`, or `XAI_API_KEY` "
        "in Admin → API Keys. Alternatively, use the **Puter AI** option for free browser-side Claude."
    )

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_CHAT_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]

_CLAUDE_BASE  = "https://api.anthropic.com/v1/messages"
_CLAUDE_MODEL = "claude-3-5-haiku-20241022"

_GROK_BASE  = "https://api.x.ai/v1/chat/completions"
_GROK_MODEL = "grok-2-1212"

SYSTEM_PROMPT = (
    "You are VIT Assistant, the in-app sports-betting copilot for the VIT Sports "
    "Intelligence Network. You help users understand the platform's features "
    "(predictions, ML models, ROI/CLV analytics, the accumulator builder, the "
    "trust system, the validator network, governance, the wallet, training "
    "pipeline, AI insights, KYC, subscriptions and the developer API), reason "
    "about football fixtures, and interpret model output. Always stay grounded "
    "in the data you are given; if a question requires live data you do not "
    "have, say so. Keep responses concise, conversational, and actionable. "
    "Never give guarantees about bet outcomes or financial advice; remind users "
    "that betting carries risk."
)


def _build_gemini_contents(history: List[Dict[str, str]], message: str) -> List[Dict]:
    """Convert chat history + new message into Gemini contents format."""
    contents: List[Dict] = []
    for turn in history[-12:]:
        role = "user" if turn.get("role") == "user" else "model"
        text = (turn.get("content") or "").strip()
        if not text:
            continue
        contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": message.strip()}]})
    return contents


def _build_openai_messages(history: List[Dict[str, str]], message: str, system_text: str) -> List[Dict]:
    msgs: List[Dict] = [{"role": "system", "content": system_text}]
    for turn in history[-12:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        text = (turn.get("content") or "").strip()
        if text:
            msgs.append({"role": role, "content": text})
    msgs.append({"role": "user", "content": message.strip()})
    return msgs


async def _try_gemini(
    client: httpx.AsyncClient,
    api_key: str,
    system_text: str,
    history: List[Dict],
    message: str,
) -> Optional[Dict]:
    payload = {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": _build_gemini_contents(history, message),
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 800},
    }
    resp = None
    for model in _GEMINI_CHAT_MODELS:
        url = f"{_GEMINI_BASE}/{model}:generateContent?key={api_key}"
        try:
            resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        except httpx.TimeoutException:
            logger.debug("[chat-cascade] gemini/%s timed out", model)
            continue
        if resp.status_code not in (404, 503):
            break
        logger.debug("[chat-cascade] gemini/%s unavailable (%s), trying next", model, resp.status_code)

    if resp is None:
        return None
    if resp.status_code in (401, 403):
        logger.warning("[chat-cascade] Gemini auth error %s", resp.status_code)
        return None
    if resp.status_code == 429:
        logger.warning("[chat-cascade] Gemini rate-limited — cascading to Claude")
        return None
    if not resp.is_success:
        logger.warning("[chat-cascade] Gemini HTTP %s — cascading", resp.status_code)
        return None

    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return None
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        return None
    return {"available": True, "reply": text, "error": None, "provider": "gemini"}


async def _try_claude(
    client: httpx.AsyncClient,
    api_key: str,
    system_text: str,
    history: List[Dict],
    message: str,
) -> Optional[Dict]:
    if not api_key:
        return None

    msgs = []
    for turn in history[-12:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        text = (turn.get("content") or "").strip()
        if text:
            msgs.append({"role": role, "content": text})
    msgs.append({"role": "user", "content": message.strip()})

    payload = {
        "model": _CLAUDE_MODEL,
        "max_tokens": 800,
        "system": system_text,
        "messages": msgs,
    }
    try:
        resp = await client.post(
            _CLAUDE_BASE,
            json=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
    except httpx.TimeoutException:
        logger.warning("[chat-cascade] Claude timed out — cascading to Grok")
        return None

    if resp.status_code == 429:
        logger.warning("[chat-cascade] Claude rate-limited — cascading to Grok")
        return None
    if not resp.is_success:
        logger.warning("[chat-cascade] Claude HTTP %s — cascading", resp.status_code)
        return None

    data = resp.json()
    content_blocks = data.get("content") or []
    text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text").strip()
    if not text:
        return None
    return {"available": True, "reply": text, "error": None, "provider": "claude"}


async def _try_grok(
    client: httpx.AsyncClient,
    api_key: str,
    system_text: str,
    history: List[Dict],
    message: str,
) -> Optional[Dict]:
    if not api_key:
        return None

    payload = {
        "model": _GROK_MODEL,
        "max_tokens": 800,
        "temperature": 0.5,
        "messages": _build_openai_messages(history, message, system_text),
    }
    try:
        resp = await client.post(
            _GROK_BASE,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
    except httpx.TimeoutException:
        logger.warning("[chat-cascade] Grok timed out — all providers exhausted")
        return None

    if resp.status_code == 429:
        logger.warning("[chat-cascade] Grok rate-limited — all providers exhausted")
        return None
    if not resp.is_success:
        logger.warning("[chat-cascade] Grok HTTP %s", resp.status_code)
        return None

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return None
    text = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        return None
    return {"available": True, "reply": text, "error": None, "provider": "grok"}


async def chat(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    context: Optional[str] = None,
) -> Dict:
    """Send a chat turn through the cascade: Gemini → Claude → Grok → error.

    Returns:
        {"available": bool, "reply": str, "error": str|None, "provider": str|None}
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    claude_key = os.getenv("CLAUDE_API_KEY", "").strip()
    grok_key   = os.getenv("XAI_API_KEY", "").strip()

    if not any([gemini_key, claude_key, grok_key]):
        scie_reply = _scie_fallback_reply(message, context)
        return {
            "available": True,
            "reply": scie_reply,
            "error": None,
            "provider": "vit-statistical-engine",
        }

    if not message or not message.strip():
        return {"available": True, "reply": "Please enter a question.", "error": None, "provider": None}

    system_text = SYSTEM_PROMPT
    if context:
        system_text += f"\n\nAdditional context for this conversation:\n{context.strip()}"

    history = history or []

    try:
        async with httpx.AsyncClient(timeout=22) as client:
            if gemini_key:
                result = await _try_gemini(client, gemini_key, system_text, history, message)
                if result:
                    logger.info("[chat-cascade] Served by Gemini")
                    return result

            if claude_key:
                result = await _try_claude(client, claude_key, system_text, history, message)
                if result:
                    logger.info("[chat-cascade] Served by Claude")
                    return result

            if grok_key:
                result = await _try_grok(client, grok_key, system_text, history, message)
                if result:
                    logger.info("[chat-cascade] Served by Grok")
                    return result

        scie_reply = _scie_fallback_reply(message, context)
        logger.info("[chat-cascade] All LLM providers failed — using SCIE statistical fallback")
        return {
            "available": True,
            "reply": scie_reply,
            "error": None,
            "provider": "vit-statistical-engine",
        }

    except Exception as exc:
        logger.error("[chat-cascade] Unhandled error: %s", exc)
        scie_reply = _scie_fallback_reply(message, context)
        return {
            "available": True,
            "reply": scie_reply,
            "error": None,
            "provider": "vit-statistical-engine",
        }
