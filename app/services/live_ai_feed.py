# app/services/live_ai_feed.py
"""
Live AI Feed Service - Free AI predictions from multiple sources
Integrates with Sports Skills, Bzzoiro, and other free APIs.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)


class AISource(Enum):
    """Supported AI prediction sources"""
    SPORTS_SKILLS = "sports_skills"
    BZZOIRO = "bzzoiro"
    FOOTBALL_BIN = "football_bin"
    SPORTBOT = "sportbot"


@dataclass
class AIPredictionResult:
    """Standardized AI prediction output"""
    source: str
    match_id: str
    home_team: str
    away_team: str
    home_prob: float
    draw_prob: float
    away_prob: float
    confidence: float
    timestamp: datetime
    league: str
    raw_data: Optional[Dict] = None


class LiveAIFeedService:
    """
    Multi-source live AI feed aggregator.
    All sources are free with no API keys required when available.
    """

    def __init__(self):
        self.sources = []
        self._register_sources()

    def _register_sources(self):
        """Register available AI prediction sources."""
        try:
            from sports_skills import FootballData
            self.sports_skills = FootballData
            self.sources.append({
                "name": AISource.SPORTS_SKILLS,
                "enabled": True,
                "fetcher": self._fetch_sports_skills,
            })
            logger.info("✅ Sports Skills registered")
        except ImportError:
            logger.warning("Sports Skills not installed. Run: pip install sports-skills")
            self.sources.append({
                "name": AISource.SPORTS_SKILLS,
                "enabled": False,
                "fetcher": None,
            })

        bzzoiro_key = os.getenv("BZZOIRO_API_KEY", "")
        if bzzoiro_key:
            self.sources.append({
                "name": AISource.BZZOIRO,
                "enabled": True,
                "api_key": bzzoiro_key,
                "fetcher": self._fetch_bzzoiro,
            })
            logger.info("✅ Bzzoiro registered")
        else:
            self.sources.append({
                "name": AISource.BZZOIRO,
                "enabled": False,
                "fetcher": None,
            })

        self.sources.append({
            "name": AISource.FOOTBALL_BIN,
            "enabled": True,
            "fetcher": self._fetch_football_bin,
        })
        logger.info("✅ Football Bin registered")

        sportbot_key = os.getenv("SPORTBOT_API_KEY", "")
        if sportbot_key:
            self.sources.append({
                "name": AISource.SPORTBOT,
                "enabled": True,
                "api_key": sportbot_key,
                "fetcher": self._fetch_sportbot,
            })
            logger.info("✅ SportBot registered")
        else:
            self.sources.append({
                "name": AISource.SPORTBOT,
                "enabled": False,
                "fetcher": None,
            })

    async def _fetch_sports_skills(self, match_data: Dict) -> Optional[AIPredictionResult]:
        """Fetch prediction from Sports Skills."""
        try:
            home_team = match_data.get("home_team")
            away_team = match_data.get("away_team")
            league = match_data.get("league", "EPL")

            home_stats = self.sports_skills.get_team_stats(home_team, league)
            away_stats = self.sports_skills.get_team_stats(away_team, league)

            if not home_stats or not away_stats:
                return None

            home_xg = home_stats.get("avg_xg", 1.5)
            away_xg = away_stats.get("avg_xg", 1.2)
            home_xga = home_stats.get("avg_xga", 1.2)
            away_xga = away_stats.get("avg_xga", 1.5)

            home_attack = home_xg / (home_xg + away_xga)
            away_attack = away_xg / (away_xg + home_xga)

            home_prob = home_attack * 0.6 + 0.2
            away_prob = away_attack * 0.6 + 0.2
            draw_prob = 1 - home_prob - away_prob

            total = home_prob + draw_prob + away_prob
            home_prob /= total
            draw_prob /= total
            away_prob /= total

            return AIPredictionResult(
                source=AISource.SPORTS_SKILLS.value,
                match_id=match_data.get("match_id", ""),
                home_team=home_team,
                away_team=away_team,
                home_prob=round(home_prob, 3),
                draw_prob=round(draw_prob, 3),
                away_prob=round(away_prob, 3),
                confidence=0.68,
                timestamp=datetime.now(),
                league=league,
            )
        except Exception as e:
            logger.error(f"Sports Skills fetch failed: {e}")
            return None

    async def _fetch_bzzoiro(self, match_data: Dict) -> Optional[AIPredictionResult]:
        """Fetch prediction from Bzzoiro API."""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://sports.bzzoiro.com/api/v1/predict"
                params = {
                    "home_team": match_data.get("home_team"),
                    "away_team": match_data.get("away_team"),
                    "league": match_data.get("league", "EPL"),
                    "api_key": self._get_api_key(AISource.BZZOIRO),
                }

                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return AIPredictionResult(
                            source=AISource.BZZOIRO.value,
                            match_id=match_data.get("match_id", ""),
                            home_team=match_data.get("home_team"),
                            away_team=match_data.get("away_team"),
                            home_prob=float(data.get("home_win", 0.33)),
                            draw_prob=float(data.get("draw", 0.33)),
                            away_prob=float(data.get("away_win", 0.33)),
                            confidence=float(data.get("confidence", 0.7)),
                            timestamp=datetime.now(),
                            league=match_data.get("league", ""),
                            raw_data=data,
                        )
        except Exception as e:
            logger.error(f"Bzzoiro fetch failed: {e}")
        return None

    async def _fetch_football_bin(self, match_data: Dict) -> Optional[AIPredictionResult]:
        """Fetch prediction from Football Bin (free, no key)."""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.football-bin.com/v1/predict"
                params = {
                    "home": match_data.get("home_team"),
                    "away": match_data.get("away_team"),
                }

                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return AIPredictionResult(
                            source=AISource.FOOTBALL_BIN.value,
                            match_id=match_data.get("match_id", ""),
                            home_team=match_data.get("home_team"),
                            away_team=match_data.get("away_team"),
                            home_prob=float(data.get("home_prob", 0.33)),
                            draw_prob=float(data.get("draw_prob", 0.33)),
                            away_prob=float(data.get("away_prob", 0.33)),
                            confidence=float(data.get("confidence", 0.65)),
                            timestamp=datetime.now(),
                            league=match_data.get("league", ""),
                            raw_data=data,
                        )
        except Exception as e:
            logger.error(f"Football Bin fetch failed: {e}")
        return None

    async def _fetch_sportbot(self, match_data: Dict) -> Optional[AIPredictionResult]:
        """Fetch prediction from SportBot AI."""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.sportbot.ai/v1/predictions"
                headers = {"X-API-Key": self._get_api_key(AISource.SPORTBOT)}
                params = {
                    "home_team": match_data.get("home_team"),
                    "away_team": match_data.get("away_team"),
                    "sport": "soccer",
                }

                async with session.get(url, headers=headers, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return AIPredictionResult(
                            source=AISource.SPORTBOT.value,
                            match_id=match_data.get("match_id", ""),
                            home_team=match_data.get("home_team"),
                            away_team=match_data.get("away_team"),
                            home_prob=float(data.get("home_win_probability", 0.33)),
                            draw_prob=float(data.get("draw_probability", 0.33)),
                            away_prob=float(data.get("away_win_probability", 0.33)),
                            confidence=float(data.get("model_confidence", 0.7)),
                            timestamp=datetime.now(),
                            league=match_data.get("league", ""),
                            raw_data=data,
                        )
        except Exception as e:
            logger.error(f"SportBot fetch failed: {e}")
        return None

    def _get_api_key(self, source: AISource) -> str:
        """Get API key for a source from environment."""
        key_map = {
            AISource.BZZOIRO: "BZZOIRO_API_KEY",
            AISource.SPORTBOT: "SPORTBOT_API_KEY",
        }
        return os.getenv(key_map.get(source, ""), "")

    async def get_live_predictions(self, match_data: Dict) -> Dict[str, Any]:
        """Fetch live AI predictions from all enabled sources in parallel."""
        enabled_sources = [s for s in self.sources if s["enabled"] and s["fetcher"]]

        if not enabled_sources:
            logger.warning("No AI sources enabled")
            return self._empty_response()

        tasks = [source["fetcher"](match_data) for source in enabled_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        predictions: List[AIPredictionResult] = []
        for result in results:
            if isinstance(result, AIPredictionResult):
                predictions.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Source failed: {result}")

        if not predictions:
            return self._empty_response()

        return self._aggregate_predictions(predictions, match_data)

    def _aggregate_predictions(self, predictions: List[AIPredictionResult], match_data: Dict) -> Dict:
        """Aggregate predictions from multiple AI sources."""
        home_probs = [p.home_prob for p in predictions]
        draw_probs = [p.draw_prob for p in predictions]
        away_probs = [p.away_prob for p in predictions]

        consensus_home = sum(home_probs) / len(home_probs)
        consensus_draw = sum(draw_probs) / len(draw_probs)
        consensus_away = sum(away_probs) / len(away_probs)

        total_confidence = sum(p.confidence for p in predictions)
        if total_confidence > 0:
            weighted_home = sum(p.home_prob * p.confidence for p in predictions) / total_confidence
            weighted_draw = sum(p.draw_prob * p.confidence for p in predictions) / total_confidence
            weighted_away = sum(p.away_prob * p.confidence for p in predictions) / total_confidence
        else:
            weighted_home = weighted_draw = weighted_away = 0.33

        all_probs = home_probs + draw_probs + away_probs
        mean_prob = sum(all_probs) / len(all_probs)
        disagreement = sum((p - mean_prob) ** 2 for p in all_probs) / len(all_probs)

        max_confidence = max(p.confidence for p in predictions)
        best_source = predictions[home_probs.index(max(home_probs))].source if home_probs else None

        return {
            "has_ai_predictions": True,
            "sources_count": len(predictions),
            "sources": [p.source for p in predictions],
            "consensus": {
                "home": round(consensus_home, 3),
                "draw": round(consensus_draw, 3),
                "away": round(consensus_away, 3),
            },
            "weighted": {
                "home": round(weighted_home, 3),
                "draw": round(weighted_draw, 3),
                "away": round(weighted_away, 3),
            },
            "disagreement_score": round(disagreement, 4),
            "high_disagreement": disagreement > 0.05,
            "max_confidence": round(max_confidence, 3),
            "most_confident_source": best_source,
            "individual_predictions": [
                {
                    "source": p.source,
                    "home": p.home_prob,
                    "draw": p.draw_prob,
                    "away": p.away_prob,
                    "confidence": p.confidence,
                }
                for p in predictions
            ],
            "timestamp": datetime.now().isoformat(),
        }

    def _empty_response(self) -> Dict:
        """Return empty response when no AI predictions available."""
        return {
            "has_ai_predictions": False,
            "sources_count": 0,
            "sources": [],
            "consensus": {"home": 0.34, "draw": 0.33, "away": 0.33},
            "weighted": {"home": 0.34, "draw": 0.33, "away": 0.33},
            "disagreement_score": 0.0,
            "high_disagreement": False,
            "max_confidence": 0.5,
            "most_confident_source": None,
            "individual_predictions": [],
            "timestamp": datetime.now().isoformat(),
        }

    async def get_live_odds_and_predictions(self, match_data: Dict) -> Dict:
        """Get both AI predictions and market comparison."""
        ai_result = await self.get_live_predictions(match_data)

        market_odds = match_data.get("market_odds", {})
        if market_odds and ai_result.get("has_ai_predictions"):
            home_implied = 1 / market_odds.get("home", 2.0)
            draw_implied = 1 / market_odds.get("draw", 3.2)
            away_implied = 1 / market_odds.get("away", 2.0)
            total_implied = home_implied + draw_implied + away_implied

            market_probs = {
                "home": home_implied / total_implied,
                "draw": draw_implied / total_implied,
                "away": away_implied / total_implied,
            }

            ai_consensus = ai_result.get("consensus", {})
            ai_weighted = ai_result.get("weighted", {})

            ai_result["market_comparison"] = {
                "market_probs": {
                    "home": round(market_probs["home"], 3),
                    "draw": round(market_probs["draw"], 3),
                    "away": round(market_probs["away"], 3),
                },
                "edge_vs_market": {
                    "home": round(ai_consensus.get("home", 0.33) - market_probs["home"], 4),
                    "draw": round(ai_consensus.get("draw", 0.33) - market_probs["draw"], 4),
                    "away": round(ai_consensus.get("away", 0.33) - market_probs["away"], 4),
                },
                "weighted_edge": {
                    "home": round(ai_weighted.get("home", 0.33) - market_probs["home"], 4),
                    "draw": round(ai_weighted.get("draw", 0.33) - market_probs["draw"], 4),
                    "away": round(ai_weighted.get("away", 0.33) - market_probs["away"], 4),
                },
                "ai_agrees_with_market": max(ai_consensus.values()) == max(market_probs.values()),
            }

        return ai_result
