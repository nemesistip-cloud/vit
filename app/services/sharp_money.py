"""app/services/sharp_money.py — Sharp Money Tracker.

Monitors odds movements from stored match data.
Flags moves >2% in recent windows as potential sharp money signals.
Sends Telegram alerts when significant moves are detected.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SHARP_MOVE_THRESHOLD = 0.02      # 2% probability shift = sharp signal
_TIME_WINDOW_MINUTES  = 30        # Look back 30 minutes for rapid moves
_ALERT_COOLDOWN_SECS  = 300       # Don't re-alert same match within 5 min

# In-memory alert cooldown tracker {match_id: last_alert_ts}
_last_alerts: Dict[int, float] = {}


def _vig_free_probs(home_odds: float, draw_odds: float, away_odds: float) -> Optional[Dict[str, float]]:
    """Convert decimal odds to vig-free probabilities."""
    try:
        if min(home_odds, draw_odds, away_odds) <= 1.0:
            return None
        inv_h = 1.0 / home_odds
        inv_d = 1.0 / draw_odds
        inv_a = 1.0 / away_odds
        total = inv_h + inv_d + inv_a
        if total <= 0:
            return None
        return {
            "home": round(inv_h / total, 4),
            "draw": round(inv_d / total, 4),
            "away": round(inv_a / total, 4),
        }
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _prob_move(old_prob: float, new_prob: float) -> float:
    """Return signed probability move (new - old)."""
    return round(new_prob - old_prob, 4)


def _is_sharp(move: float) -> bool:
    """Flag as sharp if absolute move exceeds threshold."""
    return abs(move) >= _SHARP_MOVE_THRESHOLD


def analyze_odds_movement(
    match_id: int,
    home_team: str,
    away_team: str,
    opening_odds_home: Optional[float],
    opening_odds_draw: Optional[float],
    opening_odds_away: Optional[float],
    current_odds_home: Optional[float],
    current_odds_draw: Optional[float],
    current_odds_away: Optional[float],
) -> Dict[str, Any]:
    """
    Compare opening vs current odds for a match and detect sharp money signals.

    Returns a dict with:
        moves: {home, draw, away} probability shifts
        sharp_signals: list of flagged sides
        steam_direction: 'home' | 'draw' | 'away' | None
        alert_required: bool
        summary: human-readable string
    """
    if not all([opening_odds_home, opening_odds_draw, opening_odds_away]):
        return {"sharp_signals": [], "alert_required": False, "summary": "No opening odds available"}
    if not all([current_odds_home, current_odds_draw, current_odds_away]):
        return {"sharp_signals": [], "alert_required": False, "summary": "No current odds available"}

    open_probs = _vig_free_probs(opening_odds_home, opening_odds_draw, opening_odds_away)
    curr_probs  = _vig_free_probs(current_odds_home, current_odds_draw, current_odds_away)

    if not open_probs or not curr_probs:
        return {"sharp_signals": [], "alert_required": False, "summary": "Invalid odds data"}

    moves = {
        "home": _prob_move(open_probs["home"], curr_probs["home"]),
        "draw": _prob_move(open_probs["draw"], curr_probs["draw"]),
        "away": _prob_move(open_probs["away"], curr_probs["away"]),
    }

    sharp_signals = [side for side, move in moves.items() if _is_sharp(move)]

    # Steam direction = side with largest absolute move toward lower price
    steam_side = max(moves, key=lambda s: abs(moves[s]))
    steam_direction = steam_side if _is_sharp(moves[steam_side]) else None

    # Cooldown check
    now = datetime.now(timezone.utc).timestamp()
    last = _last_alerts.get(match_id, 0)
    alert_required = bool(sharp_signals) and (now - last) > _ALERT_COOLDOWN_SECS

    if alert_required:
        _last_alerts[match_id] = now

    move_strs = [f"{s.upper()} {moves[s]:+.1%}" for s in sharp_signals]
    summary = (
        f"Sharp money detected: {', '.join(move_strs)} on {home_team} vs {away_team}"
        if sharp_signals
        else f"No sharp movement on {home_team} vs {away_team}"
    )

    return {
        "match_id":       match_id,
        "home_team":      home_team,
        "away_team":      away_team,
        "opening_probs":  open_probs,
        "current_probs":  curr_probs,
        "moves":          moves,
        "sharp_signals":  sharp_signals,
        "steam_direction": steam_direction,
        "alert_required": alert_required,
        "summary":        summary,
    }


async def scan_all_sharp_movements(db) -> List[Dict[str, Any]]:
    """
    Scan all upcoming matches for sharp money movements.
    Returns list of matches with detected signals.
    """
    from app.db.models import Match
    from sqlalchemy import select, and_
    from datetime import datetime, timezone, timedelta

    signals = []
    try:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Match)
            .where(
                Match.status == "upcoming",
                Match.kickoff_time > now,
                Match.kickoff_time < now + timedelta(days=3),
                Match.opening_odds_home.isnot(None),
                Match.closing_odds_home.isnot(None),
            )
        )
        rows = list((await db.execute(stmt)).scalars().all())

        for m in rows:
            result = analyze_odds_movement(
                match_id=m.id,
                home_team=m.home_team,
                away_team=m.away_team,
                opening_odds_home=m.opening_odds_home,
                opening_odds_draw=m.opening_odds_draw,
                opening_odds_away=m.opening_odds_away,
                current_odds_home=m.closing_odds_home,
                current_odds_draw=m.closing_odds_draw,
                current_odds_away=m.closing_odds_away,
            )
            if result.get("sharp_signals"):
                result["kickoff_time"] = m.kickoff_time.isoformat() if m.kickoff_time else None
                result["league"] = m.league
                signals.append(result)

                # Send Telegram alert if warranted
                if result.get("alert_required"):
                    asyncio.create_task(_send_sharp_alert(result))

    except Exception as exc:
        logger.error("[sharp-money] scan error: %s", exc)

    return signals


async def _send_sharp_alert(signal: Dict[str, Any]) -> None:
    """Send Telegram alert for sharp money movement."""
    try:
        from app.services.telegram_service import send_telegram_message
        moves = signal.get("moves", {})
        move_strs = []
        for side in signal.get("sharp_signals", []):
            move_strs.append(f"{side.upper()} {moves.get(side, 0):+.1%}")

        msg = (
            f"🚨 Sharp Money Alert\n"
            f"{signal['home_team']} vs {signal['away_team']}\n"
            f"League: {signal.get('league', 'Unknown')}\n"
            f"Steam: {signal.get('steam_direction', 'unknown').upper()}\n"
            f"Moves: {', '.join(move_strs)}\n"
            f"Kickoff: {signal.get('kickoff_time', 'Unknown')}"
        )
        await send_telegram_message(msg)
    except Exception as exc:
        logger.debug("[sharp-money] Telegram alert failed: %s", exc)
