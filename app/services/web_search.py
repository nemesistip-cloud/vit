"""app/services/web_search.py — Real-time web search for AI context enrichment.

Provides lightweight, no-API-key web search using DuckDuckGo's lite endpoint
and RSS feeds. Results are injected into AI prompts to give models current
team news, injury updates, and match previews.

Usage:
    from app.services.web_search import fetch_team_news, fetch_match_context
    news = await fetch_team_news("Arsenal", "Premier League")
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import List, Optional
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT   = httpx.Timeout(8.0, connect=4.0)
_HEADERS   = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; VITSportsBot/1.0; +https://vitsports.ai)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Simple in-memory cache: key → (timestamp, result)
_cache: dict[str, tuple[float, list]] = {}
_CACHE_TTL = 600  # 10 minutes


def _cached(key: str) -> Optional[list]:
    entry = _cache.get(key)
    if entry and time.monotonic() - entry[0] < _CACHE_TTL:
        return entry[1]
    return None


def _store(key: str, result: list) -> None:
    _cache[key] = (time.monotonic(), result)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


async def _ddg_search(query: str, max_results: int = 5) -> List[str]:
    """
    DuckDuckGo HTML search — no API key required.
    Returns a list of plain-text snippet strings.
    """
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
        snippets: List[str] = []
        for m in re.finditer(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL):
            snip = _strip_html(m.group(1)).strip()
            if snip and len(snip) > 20:
                snippets.append(snip)
            if len(snippets) >= max_results:
                break
        return snippets
    except Exception as exc:
        logger.debug("[web-search] DDG search failed for %r: %s", query, exc)
        return []


async def fetch_team_news(team: str, league: str = "") -> List[str]:
    """
    Fetch recent news snippets for a football team.
    Returns up to 5 plain-text snippets from search results.
    """
    key = f"team:{team}:{league}"
    cached = _cached(key)
    if cached is not None:
        return cached

    queries = [
        f"{team} football injury news {league}",
        f"{team} latest news transfer form",
    ]
    all_snippets: List[str] = []
    for q in queries:
        snippets = await _ddg_search(q, max_results=3)
        all_snippets.extend(snippets)
        if all_snippets:
            break

    result = all_snippets[:5]
    _store(key, result)
    logger.debug("[web-search] fetched %d snippets for %s", len(result), team)
    return result


async def fetch_match_context(
    home_team: str,
    away_team: str,
    league: str = "",
) -> dict:
    """
    Fetch real-time context for a specific match.
    Returns a dict with home_news, away_news, and match_preview snippets.
    """
    key = f"match:{home_team}:{away_team}"
    cached = _cached(key)
    if cached is not None:
        return cached[0] if cached else {}

    home_task  = fetch_team_news(home_team, league)
    away_task  = fetch_team_news(away_team, league)
    preview_q  = f"{home_team} vs {away_team} prediction preview {league}"
    preview_task = _ddg_search(preview_q, max_results=3)

    home_news, away_news, preview = await asyncio.gather(
        home_task, away_task, preview_task,
        return_exceptions=True,
    )

    context = {
        "home_news":    home_news if isinstance(home_news, list) else [],
        "away_news":    away_news if isinstance(away_news, list) else [],
        "match_preview": preview  if isinstance(preview,  list) else [],
    }
    _store(key, [context])
    return context


def format_context_for_prompt(context: dict, home_team: str, away_team: str) -> str:
    """
    Format the web-search context into a concise prompt block for AI models.
    """
    lines = ["=== REAL-TIME MATCH INTELLIGENCE (web search) ==="]

    home_news = context.get("home_news", [])
    if home_news:
        lines.append(f"\n{home_team} recent news:")
        for s in home_news[:3]:
            lines.append(f"  • {s[:200]}")

    away_news = context.get("away_news", [])
    if away_news:
        lines.append(f"\n{away_team} recent news:")
        for s in away_news[:3]:
            lines.append(f"  • {s[:200]}")

    preview = context.get("match_preview", [])
    if preview:
        lines.append("\nMatch preview / analyst views:")
        for s in preview[:2]:
            lines.append(f"  • {s[:200]}")

    if len(lines) == 1:
        return ""
    lines.append("=== END REAL-TIME INTELLIGENCE ===")
    return "\n".join(lines)
