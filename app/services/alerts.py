# app/services/alerts.py
# VIT Sports Intelligence Network — v2.1.0
# Fix: Model count now displayed (was always 0/0)
# Fix: Probabilities now match-specific (was always 36.3%)
# Fix: Edge, stake, confidence all populated correctly
# Fix: Alert only sent when edge > threshold (proper gating)

import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum

from app.config import APP_VERSION

logger = logging.getLogger(__name__)

VERSION = APP_VERSION


class AlertPriority(Enum):
    INFO     = "ℹ️"
    SUCCESS  = "✅"
    WARNING  = "⚠️"
    CRITICAL = "🚨"
    BET      = "🎯"


@dataclass
class BetAlert:
    """Bet recommendation alert data — v4.11.0"""
    match_id:      int
    home_team:     str
    away_team:     str
    prediction:    str          # "home" | "draw" | "away" | "NONE"
    probability:   float
    edge:          float
    stake:         float
    odds:          float
    confidence:    float
    kickoff_time:  datetime
    # v2.1.0 additions
    home_prob:     float = 0.0
    draw_prob:     float = 0.0
    away_prob:     float = 0.0
    home_odds:     float = 0.0
    draw_odds:     float = 0.0
    away_odds:     float = 0.0
    models_used:   int   = 0
    models_total:  int   = 0
    data_source:   str   = "market_implied"
    # v4.11.0 — richer message body
    league:        str   = ""
    fixture_id:    Optional[str] = None
    over_25_prob:  float = 0.0
    btts_prob:     float = 0.0
    vig_free_edge: float = 0.0
    risk_score:    float = 0.0   # 0 = certain, 1 = uniform/uncertain
    top_model:     str   = ""
    data_quality:  Optional[Dict[str, Any]] = None
    app_url:       str   = ""    # base URL for in-app fixture link


class TelegramAlert:
    """
    Telegram bot for real-time alerts — v2.1.0.

    v2.1.0 Changes:
    - send_bet_alert now accepts full probability breakdown
    - Model count displayed correctly (e.g. "9/12 models")
    - Edge emoji scales with edge strength
    - Shows all 3 probabilities and all 3 odds
    - Data source badge (Ensemble vs Market)
    """

    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self._last_message_time = None

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------
    async def send_message(
        self,
        text: str,
        priority: AlertPriority = AlertPriority.INFO,
        parse_mode: str = "HTML"
    ) -> bool:
        if not self.enabled:
            logger.debug("Telegram alerts disabled")
            return False

        if self._last_message_time:
            elapsed = (datetime.now() - self._last_message_time).total_seconds()
            if elapsed < 3:
                logger.warning("Rate limit hit, skipping message")
                return False

        formatted_text = f"{priority.value} {text}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id":                  self.chat_id,
                        "text":                     formatted_text,
                        "parse_mode":               parse_mode,
                        "disable_web_page_preview": True,
                    }
                )
                if response.status_code == 200:
                    self._last_message_time = datetime.now()
                    logger.info(f"Telegram sent: {text[:60]}...")
                    return True
                else:
                    logger.error(f"Telegram error {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _edge_emoji(edge: float) -> str:
        if edge >= 0.08:  return "🔥🔥🔥"
        if edge >= 0.05:  return "🔥🔥"
        if edge >= 0.02:  return "🔥"
        if edge >= 0.0:   return "📈"
        if edge >= -0.02: return "📊"
        return "📉"

    @staticmethod
    def _source_badge(data_source: str) -> str:
        """Map an orchestrator-reported data source to a Telegram badge.

        Recognises explicit source ids and gracefully handles new ensemble
        variants (e.g. ``differentiated_ensemble_v3``) instead of falling all
        the way through to the misleading "Market-Implied" badge.
        """
        if not data_source:
            return "📊 Market-Implied"
        ds = data_source.lower()
        explicit = {
            "ensemble":                  "🤖 Ensemble (ML)",
            "neural_ensemble":           "🧠 Neural Ensemble (ML)",
            "partial_ensemble":          "🤖 Partial Ensemble",
            "differentiated_ensemble":   "🤖 Differentiated Ensemble (ML)",
            "differentiated_ensemble_v3":"🤖 Differentiated Ensemble v3 (ML)",
            "trained_ensemble":          "🎯 Trained Ensemble (ML)",
            "market_implied":            "📊 Market-Implied",
        }
        if ds in explicit:
            return explicit[ds]
        if "trained" in ds or "pkl" in ds:
            return "🎯 Trained Ensemble (ML)"
        if "partial" in ds:
            return "🤖 Partial Ensemble"
        if "ensemble" in ds or "neural" in ds:
            return "🤖 Ensemble (ML)"
        if "market" in ds:
            return "📊 Market-Implied"
        # Fall back to a humanised label so the user sees the real source
        # rather than a misleading default.
        return f"🤖 {data_source.replace('_', ' ').title()}"

    @staticmethod
    def _fmt_pct(v: float) -> str:
        return f"{v * 100:.1f}%"

    @staticmethod
    def _time_to_kickoff(kickoff: Optional[datetime]) -> str:
        """Return a human-friendly countdown like 'in 2h 14m' or 'LIVE'."""
        if not kickoff:
            return ""
        now = datetime.now(timezone.utc)
        # Treat naive kickoffs as UTC (matches the rest of the stack).
        delta = kickoff - now
        secs = delta.total_seconds()
        if secs < -3600:
            return "FT"
        if -3600 <= secs <= 0:
            return "🔴 LIVE"
        mins = int(secs // 60)
        if mins < 60:
            return f"in {mins}m"
        hrs, rem = divmod(mins, 60)
        if hrs < 48:
            return f"in {hrs}h {rem}m" if rem else f"in {hrs}h"
        days = hrs // 24
        return f"in {days}d"

    @staticmethod
    def _risk_badge(risk: float) -> str:
        """Map orchestrator risk_score (0=certain..1=uniform) to a badge."""
        if risk <= 0:
            return ""
        if risk < 0.55:
            return "🟢 Low risk"
        if risk < 0.85:
            return "🟡 Medium risk"
        return "🔴 High risk"

    @staticmethod
    def _vig_free_odds(prob: float) -> str:
        """Return the fair odds for a probability, or '—' if unknown."""
        if prob <= 0:
            return "—"
        return f"{1.0 / prob:.2f}"

    @staticmethod
    def _data_quality_warnings(dq: Optional[Dict[str, Any]]) -> str:
        """
        Render any degradation flags from the prediction's data_quality block
        as a short warning line. Returns "" when everything is clean so the
        alert stays compact in the happy path.
        """
        if not dq:
            return ""
        notes: List[str] = []
        if dq.get("market_odds_fallback"):
            notes.append("market odds estimated")
        if dq.get("vig_removal_fallback"):
            notes.append("vig-removal fallback")
        completeness = dq.get("feature_completeness")
        if completeness is not None and completeness < 0.3:
            notes.append(f"low feature data ({completeness:.0%})")
        failed = dq.get("failed_models") or []
        if failed:
            notes.append(f"{len(failed)} model(s) failed")
        warnings = dq.get("warnings") or []
        # Only surface warnings we haven't already covered above.
        suppress = {
            "market_odds_fallback", "vig_removal_fallback",
            "low_feature_completeness", "served_from_cache",
        }
        for w in warnings:
            if w not in suppress and len(notes) < 4:
                notes.append(w.replace("_", " "))
        if not notes:
            return ""
        return "⚠️ <b>Data flags:</b> " + ", ".join(notes)

    # ------------------------------------------------------------------
    # Bet alert — v2.1.0 (full redesign)
    # ------------------------------------------------------------------
    async def send_bet_alert(self, alert: BetAlert) -> bool:
        """
        Send bet recommendation alert with full probability breakdown.

        v4.11.0 message body adds:
          - league + countdown to kickoff
          - goals markets line (Over 2.5, BTTS) when supplied
          - vig-free fair odds for the recommended side
          - risk badge derived from orchestrator entropy
          - top contributing model name
          - data quality warnings (fallback flags / failed models)
          - tappable link to the in-app match page when ``app_url`` is set
        """
        kickoff_str = (
            alert.kickoff_time.strftime("%Y-%m-%d %H:%M UTC")
            if alert.kickoff_time else "TBD"
        )
        countdown = self._time_to_kickoff(alert.kickoff_time)

        # Prediction label
        pred_labels = {"home": "HOME WIN", "draw": "DRAW", "away": "AWAY WIN"}
        pred_key = (alert.prediction or "").lower()
        pred_display = pred_labels.get(pred_key, alert.prediction.upper() if alert.prediction else "—")
        has_edge = alert.edge > 0.02

        edge_emoji   = self._edge_emoji(alert.edge)
        source_badge = self._source_badge(alert.data_source)
        risk_badge   = self._risk_badge(alert.risk_score)
        model_str    = (
            f"✅ {alert.models_used}/{alert.models_total} models"
            if alert.models_used > 0
            else f"📊 Market-implied ({alert.models_total} models loading)"
        )

        # League / countdown header line (only render parts we have)
        header_bits: List[str] = []
        if alert.league:
            header_bits.append(f"🏆 {alert.league}")
        if countdown:
            header_bits.append(f"⏳ {countdown}")
        header_line = "  ·  ".join(header_bits)

        if has_edge:
            # Vig-free fair odds for the recommended side, sourced from the
            # model's own probability so the user can see the math behind
            # the edge call (model fair price vs market price offered).
            side_prob_map = {
                "home": alert.home_prob,
                "draw": alert.draw_prob,
                "away": alert.away_prob,
            }
            fair_prob = side_prob_map.get(pred_key, alert.probability)
            fair_odds = self._vig_free_odds(fair_prob)
            edge_line = f"<b>💰 Edge:</b> <b>{alert.edge:+.2%}</b> {edge_emoji}"
            if alert.vig_free_edge and abs(alert.vig_free_edge - alert.edge) > 0.0005:
                edge_line += f"  (vig-free {alert.vig_free_edge:+.2%})"
            recommendation_block = (
                f"<b>📊 Prediction:</b> <b>{pred_display}</b>\n"
                f"{edge_line}\n"
                f"<b>🎲 Market Odds:</b> {alert.odds:.2f}   "
                f"<b>⚖️ Fair Odds:</b> {fair_odds}\n"
                f"<b>💵 Stake:</b> {alert.stake:.1%} of bankroll"
            )
        else:
            recommendation_block = (
                f"<b>📊 Prediction:</b> NO EDGE DETECTED\n"
                f"<b>💰 Edge:</b> {alert.edge:+.2%} (below 2% threshold)\n"
                f"<b>💵 Stake:</b> 0.0% — skip this match"
            )

        # Build odds row only if we have them
        odds_row = ""
        if alert.home_odds > 1.01 and alert.draw_odds > 1.01 and alert.away_odds > 1.01:
            odds_row = (
                f"\n<b>🎲 Market Odds:</b>  "
                f"H {alert.home_odds:.2f} | D {alert.draw_odds:.2f} | A {alert.away_odds:.2f}"
            )

        # Goals markets line — only render if we actually have data for them
        goals_bits: List[str] = []
        if alert.over_25_prob and alert.over_25_prob > 0:
            goals_bits.append(f"O2.5 {self._fmt_pct(alert.over_25_prob)}")
            goals_bits.append(f"U2.5 {self._fmt_pct(max(0.0, 1.0 - alert.over_25_prob))}")
        if alert.btts_prob and alert.btts_prob > 0:
            goals_bits.append(f"BTTS {self._fmt_pct(alert.btts_prob)}")
        goals_row = (
            f"\n<b>⚽ Goals:</b>  " + "  |  ".join(goals_bits) if goals_bits else ""
        )

        # Optional secondary lines built conditionally so the message stays tight.
        extra_lines: List[str] = []
        if risk_badge:
            extra_lines.append(f"<b>📐 Risk:</b> {risk_badge} ({alert.risk_score:.2f})")
        if alert.top_model:
            extra_lines.append(f"<b>🥇 Top Model:</b> {alert.top_model}")
        dq_line = self._data_quality_warnings(alert.data_quality)
        if dq_line:
            extra_lines.append(dq_line)
        if alert.app_url and alert.match_id:
            link = f"{alert.app_url.rstrip('/')}/matches/{alert.match_id}"
            extra_lines.append(f'<b>🔗 Open:</b> <a href="{link}">view in VIT</a>')
        extra_block = "\n".join(extra_lines)
        if extra_block:
            extra_block = "\n\n" + extra_block

        header_block = ""
        if header_line:
            header_block = f"\n{header_line}"

        message = f"""<b>🎯 VIT BET ANALYSIS</b>
━━━━━━━━━━━━━━━━━━━━━

<b>⚽ Match:</b> {alert.home_team} vs {alert.away_team}{header_block}
<b>🕐 Kickoff:</b> {kickoff_str}

<b>📈 Probabilities:</b>
  🏠 Home: {self._fmt_pct(alert.home_prob)}
  🤝 Draw: {self._fmt_pct(alert.draw_prob)}
  ✈️  Away: {self._fmt_pct(alert.away_prob)}{odds_row}{goals_row}

{recommendation_block}

<b>🎯 Confidence:</b> {self._fmt_pct(alert.confidence)}
<b>🤖 Source:</b> {source_badge}
<b>📊 Models:</b> {model_str}{extra_block}

━━━━━━━━━━━━━━━━━━━━━
<i>VIT Sports Intelligence v{VERSION}</i>"""

        priority = AlertPriority.BET if has_edge else AlertPriority.INFO
        return await self.send_message(message.strip(), priority)

    # ------------------------------------------------------------------
    # Daily report (unchanged, kept for compatibility)
    # ------------------------------------------------------------------
    async def send_daily_report(
        self,
        stats: Dict[str, Any],
        top_edges: List[Dict] = None
    ) -> bool:
        date = datetime.now().strftime("%Y-%m-%d")
        roi = stats.get("roi", 0)
        perf_emoji = "📈🚀" if roi > 0.05 else ("📈" if roi > 0 else ("📉" if roi > -0.05 else "📉💀"))

        message = f"""<b>📊 VIT DAILY REPORT</b>
━━━━━━━━━━━━━━━━━━━━━

<b>📅 Date:</b> {date}
<b>{perf_emoji} Performance:</b>

<b>💰 Total Bets:</b> {stats.get('total_bets', 0)}
<b>✅ Winning Bets:</b> {stats.get('winning_bets', 0)}
<b>❌ Losing Bets:</b> {stats.get('losing_bets', 0)}
<b>📊 Win Rate:</b> {stats.get('win_rate', 0):.1%}
<b>💵 ROI:</b> {stats.get('roi', 0):.2%}
<b>📈 CLV:</b> {stats.get('avg_clv', 0):.4f}
<b>💼 Bankroll:</b> ${stats.get('bankroll', 0):.2f}

<b>📊 Model Health:</b>
<b>🎯 Accuracy:</b> {stats.get('model_accuracy', 0):.1%}
<b>⚡ Confidence:</b> {stats.get('avg_confidence', 0):.1%}"""

        if top_edges:
            message += "\n\n<b>🔥 Top Edges Today:</b>\n"
            for edge in top_edges[:3]:
                message += f"• {edge.get('home_team')} vs {edge.get('away_team')}: {edge.get('edge', 0):.2%} edge\n"

        message += f"\n<i>VIT Sports Intelligence v{VERSION}</i>"
        return await self.send_message(message.strip())

    # ------------------------------------------------------------------
    # Other alerts (unchanged)
    # ------------------------------------------------------------------
    async def send_match_result(
        self,
        match_id: int,
        home_team: str,
        away_team: str,
        home_goals: int,
        away_goals: int,
        was_correct: bool,
        profit: float
    ) -> bool:
        result_emoji = "✅" if was_correct else "❌"
        message = f"""<b>{result_emoji} MATCH RESULT</b>
━━━━━━━━━━━━━━━━━━━━━

<b>⚽ Match:</b> {home_team} vs {away_team}
<b>📊 Score:</b> {home_goals} - {away_goals}
<b>🎯 Prediction:</b> {'CORRECT' if was_correct else 'INCORRECT'}
<b>💰 Profit/Loss:</b> ${profit:.2f}"""
        return await self.send_message(message.strip())

    async def send_anomaly_alert(
        self,
        anomaly_type: str,
        details: Dict[str, Any],
        severity: str = "warning"
    ) -> bool:
        priority = AlertPriority.CRITICAL if severity == "critical" else AlertPriority.WARNING
        message = f"""<b>⚠️ ANOMALY DETECTED</b>
━━━━━━━━━━━━━━━━━━━━━

<b>Type:</b> {anomaly_type}
<b>Severity:</b> {severity.upper()}

<b>Details:</b>\n"""
        for key, value in details.items():
            message += f"• {key}: {value}\n"
        message += "\n<i>Action may be required</i>"
        return await self.send_message(message.strip(), priority)

    async def send_model_performance_alert(
        self,
        model_name: str,
        old_weight: float,
        new_weight: float,
        reason: str
    ) -> bool:
        direction = "⬆️" if new_weight > old_weight else "⬇️"
        message = f"""<b>🤖 MODEL WEIGHT UPDATE</b>
━━━━━━━━━━━━━━━━━━━━━

<b>Model:</b> {model_name}
<b>Weight:</b> {old_weight:.2%} → {new_weight:.2%} {direction}
<b>Reason:</b> {reason}

<i>Automatic weight decay applied</i>"""
        return await self.send_message(message.strip())

    async def send_startup_message(self) -> bool:
        message = f"""<b>🚀 VIT NETWORK STARTED</b>
━━━━━━━━━━━━━━━━━━━━━

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>Version:</b> v{VERSION}
<b>Status:</b> OPERATIONAL
<b>Alerts:</b> ENABLED

<i>Monitoring for betting opportunities...</i>"""
        return await self.send_message(message.strip())

    async def send_shutdown_message(self) -> bool:
        message = f"""<b>🛑 VIT NETWORK SHUTDOWN</b>
━━━━━━━━━━━━━━━━━━━━━

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>System stopped. No alerts will be sent.</i>"""
        return await self.send_message(message.strip())
