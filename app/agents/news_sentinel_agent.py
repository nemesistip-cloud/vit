"""app/agents/news_sentinel_agent.py

NewsSentinelAgent — runs every 20 minutes.

Dual-mode operation:

Mode A — Scraper (preferred):
  Scrapes latest injuries via Transfermarkt, groups them by team, then uses
  AI to assess the impact on upcoming matches.

Mode B — VIT SCIE Fallback (no external data required):
  When the scraper returns empty (blocked / rate-limited / no data), falls
  back to querying the internal database for teams with sharp recent form
  changes and uses AI to generate team-news style intelligence briefs.
  This ensures the agent always produces reports even without live web data.

Free-tier limit protection:
  - Max 3 teams per cycle
  - 2-second pause between AI calls
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


from app.agents.base import BaseAgent
from app.services.ai_client import call_ai, call_ai_with_provider

logger = logging.getLogger(__name__)

MAX_TEAMS_PER_CYCLE = 3


def _build_news_prompt(team: str, injuries: List[Dict]) -> str:
    injury_lines = "\n".join(
        f"- {inj.get('player_name', 'Unknown')} ({inj.get('injury', 'injury')}, "
        f"status: {inj.get('status', 'unknown')})"
        for inj in injuries[:6]
    )
    return f"""You are a football injury analyst. Assess the impact of the following absences on {team}.

Current absences for {team}:
{injury_lines}

Return ONLY a JSON object (no markdown fences):
{{
  "team": "{team}",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "summary": "2-sentence impact assessment",
  "key_positions_affected": ["position1", "position2"],
  "betting_implication": "1 sentence on how this shifts the team's match odds",
  "confidence": 0.0
}}"""


def _build_form_news_prompt(team: str, form: Dict, league: str) -> str:
    """SCIE fallback: generate team news from internal form data."""
    return f"""You are a football analyst. Based on the following recent performance data for {team}, 
write an intelligence brief as if reporting team news.

Team: {team}
League: {league.replace('_', ' ').title()}
Recent Form (last {form['matches']} games): {form['form']} — W{form['wins']} D{form['draws']} L{form['losses']}
Avg goals scored: {form['avg_scored']} per game
Avg goals conceded: {form['avg_conceded']} per game

Imagine plausible reasons for this form (injuries, tactical changes, morale) 
and write a useful intelligence note. Do NOT fabricate specific player names.

Return ONLY a JSON object (no markdown fences):
{{
  "team": "{team}",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "summary": "2-sentence form-based intelligence brief",
  "key_positions_affected": ["general area if applicable"],
  "betting_implication": "1 sentence on betting implication of this form",
  "confidence": 0.0,
  "data_source": "vit_internal"
}}"""


async def _get_notable_teams_from_db(db, n: int = 6) -> List[Dict]:
    """
    SCIE fallback: find teams with notable form from the DB.

    Returns teams from recently settled matches, prioritising those with
    unusual win/loss streaks (≥3 consecutive outcomes).
    """
    from sqlalchemy import select, or_
    from app.db.models import Match

    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=14)

    try:
        rows = (await db.execute(
            select(Match)
            .where(
                Match.status == "settled",
                Match.kickoff_time >= cutoff,
                Match.actual_outcome.is_not(None),
            )
            .order_by(Match.kickoff_time.desc())
            .limit(100)
        )).scalars().all()
    except Exception as exc:
        logger.warning("[news-sentinel] DB fallback query failed: %s", exc)
        return []

    if not rows:
        return []

    # Collect teams and their matches
    team_matches: Dict[str, List] = {}
    for m in rows:
        for team, is_home in [(m.home_team, True), (m.away_team, False)]:
            if not team:
                continue
            if team not in team_matches:
                team_matches[team] = []
            team_matches[team].append({
                "outcome": m.actual_outcome,
                "is_home": is_home,
                "league":  m.league or "unknown",
            })

    # Score teams by form variance (long streaks = more interesting)
    scored: List[Dict] = []
    for team, matches in team_matches.items():
        if len(matches) < 3:
            continue
        wins = sum(1 for mt in matches if
                   (mt["outcome"] == "home" and mt["is_home"]) or
                   (mt["outcome"] == "away" and not mt["is_home"]))
        losses = sum(1 for mt in matches if
                     (mt["outcome"] == "home" and not mt["is_home"]) or
                     (mt["outcome"] == "away" and mt["is_home"]))
        # Streak score: teams on hot/cold streaks are most newsworthy
        recent = matches[:5]
        recent_wins   = sum(1 for mt in recent if
                            (mt["outcome"] == "home" and mt["is_home"]) or
                            (mt["outcome"] == "away" and not mt["is_home"]))
        recent_losses = sum(1 for mt in recent if
                            (mt["outcome"] == "home" and not mt["is_home"]) or
                            (mt["outcome"] == "away" and mt["is_home"]))
        streak_score = max(recent_wins, recent_losses)
        league = matches[0]["league"] if matches else "unknown"
        scored.append({
            "team":         team,
            "league":       league,
            "matches":      len(matches),
            "wins":         wins,
            "losses":       losses,
            "streak_score": streak_score,
        })

    scored.sort(key=lambda x: x["streak_score"], reverse=True)
    return scored[:n]


class NewsSentinelAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="news-sentinel",
            interval_seconds=20 * 60,
            initial_delay_seconds=90,
        )

    async def run_cycle(self) -> Dict[str, Any]:

        from app.services.scraper import InjuryScraper
        from app.db.database import AsyncSessionLocal
        from app.db.models import AgentInsight
        from app.iot.processor import store_and_broadcast
        from app.services.vit_intelligence import get_team_form
        from app.services.sentiment_analysis import analyze_market_sentiment

        scraper = InjuryScraper()
        try:
            all_injuries = await scraper.fetch_all_injuries()
        except Exception as e:
            logger.info("[news-sentinel] scraper unavailable: %s — using SCIE fallback", e)
            all_injuries = []

        # ── Mode A: Injury Scraper ────────────────────────────────────────────
        if not all_injuries:
            logger.info("[news-sentinel] scraper returned no data — switching to SCIE fallback")

        if all_injuries:
            team_map: Dict[str, List[Dict]] = {}
            for inj in all_injuries:
                team = inj.get("team", "Unknown")
                if team and team != "Unknown":
                    team_map.setdefault(team, []).append(inj)

            high_impact_teams = sorted(
                team_map.items(), key=lambda x: len(x[1]), reverse=True
            )[:MAX_TEAMS_PER_CYCLE]

            insights_stored = 0
            teams_analyzed: List[str] = []

            for team, injuries in high_impact_teams:
                prompt = _build_news_prompt(team, injuries)
                _ai_result = await call_ai_with_provider(prompt)
                _provider_used = "scie"

                import json as _json
                # SCIE fallback: generate structured template brief when AI is unavailable
                if _ai_result:
                    raw, _provider_used = _ai_result
                else:
                    raw = None
                if not raw:
                    n = len(injuries)
                    players = ", ".join(
                        i.get("player_name", "Unknown") for i in injuries[:4]
                    )
                    raw = _json.dumps({
                        "summary": (
                            f"{team} has {n} absence(s) currently: {players}. "
                            f"Squad depth may be tested — monitor team sheets before kickoff."
                        ),
                        "severity": "MEDIUM" if n >= 3 else "LOW",
                        "confidence": 0.55,
                        "key_factors": [
                            f"{n} player(s) unavailable",
                            "Squad rotation likely",
                        ],
                        "generated_by": "SCIE-template",
                    })
                try:
                    text = raw.strip()
                    fence_match = __import__('re').search(r"```(?:json)?\s*([\s\S]*?)```", text)
                    if fence_match:
                        text = fence_match.group(1).strip()
                    elif text.startswith("```"):
                        text = text[3:]
                        if text.startswith("json"):
                            text = text[4:]
                        text = text.rstrip("`").strip()
                    parsed = _json.loads(text.strip())
                    content    = parsed.get("summary", raw[:300])
                    confidence = float(parsed.get("confidence", 0.65))
                    meta       = {**parsed, "injury_count": len(injuries)}
                except Exception:
                    content    = raw[:500]
                    confidence = 0.5
                    meta       = {"injury_count": len(injuries)}

                async with AsyncSessionLocal() as db:
                    insight = AgentInsight(
                        agent_name="news-sentinel",
                        insight_type="team_news",
                        match_id=None,
                        team=team,
                        ai_provider=_provider_used,
                        content=content,
                        meta=meta,
                        confidence=confidence,
                    )
                    db.add(insight)
                    await db.commit()

                await store_and_broadcast(
                    source="agent",
                    event_type="injury_update",
                    match_id=None,
                    payload={
                        "agent":    "news-sentinel",
                        "team":     team,
                        "severity": meta.get("severity", "UNKNOWN"),
                        "summary":  content,
                        "injuries": len(injuries),
                    },
                )

                # --- Market Sentiment Analysis (Phase 2) ---
                news_texts = [content] + [i.get('injury', '') for i in injuries]
                # NewsSentinel focuses on single team news, so we map it to home_team for sentiment context
                sentiment = await analyze_market_sentiment(
                    match_id=0, home_team=team, away_team="Opposition",
                    news_snippets=news_texts
                )
                meta["market_sentiment"] = sentiment

                teams_analyzed.append(team)
                insights_stored += 1
                await asyncio.sleep(2)

            logger.info("[news-sentinel] scraper mode: %d teams, %d injuries",
                        insights_stored, len(all_injuries))
            return {
                "mode":            "scraper",
                "teams_analyzed":  teams_analyzed,
                "insights_stored": insights_stored,
                "injuries_found":  len(all_injuries),
            }

        # ── Mode B: SCIE DB Fallback ──────────────────────────────────────────
        logger.info("[news-sentinel] using SCIE DB fallback for team intelligence")

        async with AsyncSessionLocal() as db:
            notable = await _get_notable_teams_from_db(db, n=MAX_TEAMS_PER_CYCLE * 2)
            if not notable:
                return {"mode": "scie", "teams_analyzed": [], "insights_stored": 0, "injuries_found": 0}

            insights_stored = 0
            teams_analyzed: List[str] = []

            import json as _json

            for entry in notable[:MAX_TEAMS_PER_CYCLE]:
                team   = entry["team"]
                league = entry["league"]

                form = await get_team_form(team, db, n=5)
                if form["matches"] < 2:
                    continue

                prompt = _build_form_news_prompt(team, form, league)
                _form_result = await call_ai_with_provider(prompt)
                if not _form_result:
                    continue
                raw, _form_provider = _form_result

                try:
                    text = raw.strip()
                    if text.startswith("```"):
                        text = text.split("```")[1]
                        if text.startswith("json"):
                            text = text[4:]
                    parsed     = _json.loads(text.strip())
                    content    = parsed.get("summary", raw[:300])
                    confidence = float(parsed.get("confidence", 0.6))
                    meta       = {**parsed, **form, "data_source": "vit_scie"}
                except Exception:
                    content    = raw[:500]
                    confidence = 0.5
                    meta       = {**form, "data_source": "vit_scie"}

                insight = AgentInsight(
                    agent_name="news-sentinel",
                    insight_type="team_news",
                    match_id=None,
                    team=team,
                    ai_provider=_form_provider,
                    content=content,
                    meta=meta,
                    confidence=confidence,
                )
                db.add(insight)

                await store_and_broadcast(
                    source="agent",
                    event_type="injury_update",
                    match_id=None,
                    payload={
                        "agent":    "news-sentinel",
                        "team":     team,
                        "severity": meta.get("severity", "LOW"),
                        "summary":  content,
                        "source":   "vit_scie",
                    },
                )

                # --- Market Sentiment Analysis (Phase 2) ---
                sentiment = await analyze_market_sentiment(
                    match_id=0, home_team=team, away_team="Opposition",
                    news_snippets=[content]
                )
                meta["market_sentiment"] = sentiment

                teams_analyzed.append(team)
                insights_stored += 1
                await asyncio.sleep(2)

            await db.commit()

        logger.info("[news-sentinel] SCIE mode: %d teams analyzed", insights_stored)
        return {
            "mode":            "scie",
            "teams_analyzed":  teams_analyzed,
            "insights_stored": insights_stored,
            "injuries_found":  0,
        }
