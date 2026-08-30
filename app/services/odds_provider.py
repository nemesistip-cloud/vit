"""
Odds Intelligence Layer, Provider Adapters, and Provider Health Matrix.

This module establishes a sport-agnostic multi-provider sports gateway.
It normalizes odds from diverse providers/bookmakers, detects anomalies,
computes vig-free market consensus, evaluates odds freshness, and maintains
a dynamic Provider Health Matrix across supported sports.
"""

from __future__ import annotations

import logging
import math
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OddsFreshness(str, Enum):
    LIVE = "LIVE"          # < 60 seconds
    FRESH = "FRESH"        # < 5 minutes
    ACCEPTABLE = "ACCEPTABLE" # < 30 minutes
    STALE = "STALE"        # 30-120 minutes
    INVALID = "INVALID"    # > 120 minutes


@dataclass
class NormalizedOdds:
    fixture_id: str
    sport: str
    market: str          # e.g., 'match_winner', 'over_2_5', 'btts'
    selection: str       # e.g., 'home', 'draw', 'away', 'over', 'under'
    odds: float
    bookmaker: str
    timestamp: datetime
    provider: str
    source_quality: float = 1.0  # Quality score 0.0 - 1.0

    @property
    def age_seconds(self) -> float:
        now = datetime.now(timezone.utc)
        ts = self.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return max(0.0, (now - ts).total_seconds())

    @property
    def freshness(self) -> OddsFreshness:
        age = self.age_seconds
        if age < 60:
            return OddsFreshness.LIVE
        elif age < 300:
            return OddsFreshness.FRESH
        elif age < 1800:
            return OddsFreshness.ACCEPTABLE
        elif age < 7200:
            return OddsFreshness.STALE
        else:
            return OddsFreshness.INVALID


@dataclass
class ReconciledMarketOdds:
    market: str
    sport: str
    consensus_odds: Dict[str, float]          # e.g. {"home": 2.10, "draw": 3.25, "away": 3.60}
    vig_free_probabilities: Dict[str, float]  # e.g. {"home": 0.45, "draw": 0.29, "away": 0.26}
    vig_free_odds: Dict[str, float]           # 1.0 / vig_free_probabilities
    margin: float                             # Original bookmaker overround margin (e.g. 0.05 = 5%)
    freshness: OddsFreshness
    bookmaker_count: int
    has_anomaly: bool = False
    anomaly_reason: Optional[str] = None
    provider_sources: List[str] = field(default_factory=list)
    raw_odds_count: int = 0
    odds_age_seconds: float = 0.0


class BaseSportsProvider(ABC):
    """Abstract interface for general sports data providers."""

    @abstractmethod
    async def get_fixtures(self, sport: str, league: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_fixture(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_statistics(self, fixture_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_team_form(self, team_id: str, sport: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_player_data(self, team_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_injuries(self, fixture_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_odds(self, fixture_id: str, sport: str) -> List[NormalizedOdds]:
        pass


class BaseOddsProvider(ABC):
    """Abstract interface specialized for odds retrieval and metadata."""

    @abstractmethod
    async def get_odds(self, fixture_id: str, sport: str) -> List[NormalizedOdds]:
        pass

    @abstractmethod
    def supported_sports(self) -> List[str]:
        pass

    @abstractmethod
    def supported_markets(self) -> List[str]:
        pass

    @abstractmethod
    def bookmaker_count(self) -> int:
        pass

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        pass


class OddsAPIProviderAdapter(BaseOddsProvider):
    """Adapter for The Odds API client."""

    def __init__(self, odds_api_client=None):
        self.client = odds_api_client

    def supported_sports(self) -> List[str]:
        return ["football", "basketball", "tennis", "baseball", "ice_hockey"]

    def supported_markets(self) -> List[str]:
        return ["match_winner", "over_2_5", "btts", "spreads"]

    def bookmaker_count(self) -> int:
        return 12

    async def health(self) -> Dict[str, Any]:
        return {
            "provider": "The Odds API",
            "status": "online" if self.client else "degraded",
            "supported_sports": self.supported_sports(),
        }

    async def get_odds(self, fixture_id: str, sport: str) -> List[NormalizedOdds]:
        if not self.client:
            return []
        try:
            raw_data = await self.client.get_match_odds(fixture_id, sport=sport)
            return self._normalize(raw_data, fixture_id, sport)
        except Exception as exc:
            logger.warning(f"[OddsAPIProviderAdapter] Failed to fetch odds for {fixture_id}: {exc}")
            return []

    def _normalize(self, raw_data: Any, fixture_id: str, sport: str) -> List[NormalizedOdds]:
        normalized = []
        if not raw_data:
            return normalized
        now = datetime.now(timezone.utc)

        # Handle dict or OddsData model format
        if hasattr(raw_data, "home_win") and raw_data.home_win and raw_data.home_win > 1.0:
            normalized.append(NormalizedOdds(
                fixture_id=str(fixture_id),
                sport=sport,
                market="match_winner",
                selection="home",
                odds=float(raw_data.home_win),
                bookmaker=getattr(raw_data, "bookmaker", "OddsAPI_Consensus") or "OddsAPI",
                timestamp=now,
                provider="the_odds_api",
                source_quality=0.95,
            ))
            if getattr(raw_data, "draw", None) and float(raw_data.draw) > 1.0:
                normalized.append(NormalizedOdds(
                    fixture_id=str(fixture_id),
                    sport=sport,
                    market="match_winner",
                    selection="draw",
                    odds=float(raw_data.draw),
                    bookmaker=getattr(raw_data, "bookmaker", "OddsAPI_Consensus") or "OddsAPI",
                    timestamp=now,
                    provider="the_odds_api",
                    source_quality=0.95,
                ))
            if getattr(raw_data, "away_win", None) and float(raw_data.away_win) > 1.0:
                normalized.append(NormalizedOdds(
                    fixture_id=str(fixture_id),
                    sport=sport,
                    market="match_winner",
                    selection="away",
                    odds=float(raw_data.away_win),
                    bookmaker=getattr(raw_data, "bookmaker", "OddsAPI_Consensus") or "OddsAPI",
                    timestamp=now,
                    provider="the_odds_api",
                    source_quality=0.95,
                ))
        elif isinstance(raw_data, dict):
            # Parse dict format
            bm_name = raw_data.get("bookmaker", "the_odds_api")
            for m_key, m_name in [("home", "home"), ("draw", "draw"), ("away", "away")]:
                val = raw_data.get(m_key) or raw_data.get(f"{m_key}_odds")
                if val and float(val) > 1.0:
                    normalized.append(NormalizedOdds(
                        fixture_id=str(fixture_id),
                        sport=sport,
                        market="match_winner",
                        selection=m_name,
                        odds=float(val),
                        bookmaker=bm_name,
                        timestamp=now,
                        provider="the_odds_api",
                        source_quality=0.90,
                    ))
        return normalized


class ISportsProviderAdapter(BaseOddsProvider):
    """Adapter for iSports API client."""

    def __init__(self, isports_client=None):
        self.client = isports_client

    def supported_sports(self) -> List[str]:
        return ["football", "basketball"]

    def supported_markets(self) -> List[str]:
        return ["match_winner"]

    def bookmaker_count(self) -> int:
        return 4

    async def health(self) -> Dict[str, Any]:
        return {
            "provider": "iSports API",
            "status": "online" if self.client else "degraded",
            "supported_sports": self.supported_sports(),
        }

    async def get_odds(self, fixture_id: str, sport: str) -> List[NormalizedOdds]:
        if not self.client:
            return []
        try:
            raw_data = await self.client.get_odds(fixture_id)
            return self._normalize(raw_data, fixture_id, sport)
        except Exception as exc:
            logger.warning(f"[ISportsProviderAdapter] Failed to fetch odds for {fixture_id}: {exc}")
            return []

    def _normalize(self, raw_data: Any, fixture_id: str, sport: str) -> List[NormalizedOdds]:
        normalized = []
        if not isinstance(raw_data, dict):
            return normalized
        now = datetime.now(timezone.utc)
        home = raw_data.get("home_odds") or raw_data.get("home")
        draw = raw_data.get("draw_odds") or raw_data.get("draw")
        away = raw_data.get("away_odds") or raw_data.get("away")

        if home and float(home) > 1.0:
            normalized.append(NormalizedOdds(
                fixture_id=str(fixture_id),
                sport=sport,
                market="match_winner",
                selection="home",
                odds=float(home),
                bookmaker="iSports",
                timestamp=now,
                provider="isports",
                source_quality=0.85,
            ))
        if draw and float(draw) > 1.0:
            normalized.append(NormalizedOdds(
                fixture_id=str(fixture_id),
                sport=sport,
                market="match_winner",
                selection="draw",
                odds=float(draw),
                bookmaker="iSports",
                timestamp=now,
                provider="isports",
                source_quality=0.85,
            ))
        if away and float(away) > 1.0:
            normalized.append(NormalizedOdds(
                fixture_id=str(fixture_id),
                sport=sport,
                market="match_winner",
                selection="away",
                odds=float(away),
                bookmaker="iSports",
                timestamp=now,
                provider="isports",
                source_quality=0.85,
            ))
        return normalized


class FootballDataProviderAdapter(BaseOddsProvider):
    """Adapter for Football-Data.org API client."""

    def __init__(self, football_client=None):
        self.client = football_client

    def supported_sports(self) -> List[str]:
        return ["football"]

    def supported_markets(self) -> List[str]:
        return ["match_winner"]

    def bookmaker_count(self) -> int:
        return 2

    async def health(self) -> Dict[str, Any]:
        return {
            "provider": "Football-Data.org",
            "status": "online" if self.client else "degraded",
            "supported_sports": self.supported_sports(),
        }

    async def get_odds(self, fixture_id: str, sport: str) -> List[NormalizedOdds]:
        return []


class SportsDBProviderAdapter(BaseOddsProvider):
    """Adapter for TheSportsDB API client."""

    def __init__(self, sportsdb_client=None):
        self.client = sportsdb_client

    def supported_sports(self) -> List[str]:
        return ["football", "basketball", "tennis", "baseball", "ice_hockey"]

    def supported_markets(self) -> List[str]:
        return ["match_winner"]

    def bookmaker_count(self) -> int:
        return 1

    async def health(self) -> Dict[str, Any]:
        return {
            "provider": "TheSportsDB",
            "status": "online" if self.client else "degraded",
            "supported_sports": self.supported_sports(),
        }

    async def get_odds(self, fixture_id: str, sport: str) -> List[NormalizedOdds]:
        return []


class OddsIntelligence:
    """
    Reconciles multi-provider odds, evaluates freshness, detects anomalies,
    and calculates vig-free market consensus probabilities and odds.
    """

    @staticmethod
    def reconcile(
        odds_list: List[NormalizedOdds],
        sport: str = "football",
        market: str = "match_winner"
    ) -> Optional[ReconciledMarketOdds]:
        """
        Reconcile a collection of NormalizedOdds into a single consensus structure.
        Strictly bans manufacturing missing odds. Returns None if no odds exist.
        """
        if not odds_list:
            return None

        # Filter valid decimal odds (> 1.0)
        valid_odds = [o for o in odds_list if o.odds > 1.0 and o.freshness != OddsFreshness.INVALID]
        if not valid_odds:
            return None

        selections: Dict[str, List[float]] = {}
        bookmakers = set()
        providers = set()
        timestamps = []

        for item in valid_odds:
            if item.selection not in selections:
                selections[item.selection] = []
            selections[item.selection].append(item.odds)
            bookmakers.add(item.bookmaker)
            providers.add(item.provider)
            timestamps.append(item.timestamp)

        # Basic selection requirement: for match_winner in 2-way sports (basketball, tennis), home/away required.
        # For football, home/draw/away expected.
        is_two_way = sport.lower() in ("basketball", "tennis", "baseball")
        required_selections = ["home", "away"] if is_two_way else ["home", "draw", "away"]

        for req in required_selections:
            if req not in selections or not selections[req]:
                logger.info(f"[OddsIntelligence] Incomplete selection data for {market}: missing {req}")
                return None

        # Detect anomalies & compute median/consensus prices
        consensus_odds: Dict[str, float] = {}
        has_anomaly = False
        anomaly_reasons = []

        for sel, prices in selections.items():
            if len(prices) > 1:
                min_p = min(prices)
                max_p = max(prices)
                # Anomaly check: price variation ratio > 1.35
                if max_p / min_p > 1.35:
                    has_anomaly = True
                    anomaly_reasons.append(f"ODDS_ANOMALY: High variance in {sel} odds ({min_p:.2f} - {max_p:.2f})")
            consensus_odds[sel] = round(float(statistics.median(prices)), 3)

        # Calculate implied probabilities and remove overround (vig)
        raw_implied_probs = {sel: 1.0 / price for sel, price in consensus_odds.items()}
        total_implied = sum(raw_implied_probs.values())
        margin = max(0.0, total_implied - 1.0)

        vig_free_probs: Dict[str, float] = {}
        vig_free_odds: Dict[str, float] = {}

        for sel, raw_p in raw_implied_probs.items():
            vf_p = round(raw_p / total_implied, 4) if total_implied > 0 else 0.0
            vig_free_probs[sel] = vf_p
            vig_free_odds[sel] = round(1.0 / vf_p, 3) if vf_p > 0 else 999.0

        # Overall freshness
        most_recent_ts = max(timestamps) if timestamps else datetime.now(timezone.utc)
        sample = NormalizedOdds(
            fixture_id=valid_odds[0].fixture_id,
            sport=sport,
            market=market,
            selection="home",
            odds=2.0,
            bookmaker="test",
            timestamp=most_recent_ts,
            provider="test",
        )

        avg_age = statistics.mean([o.age_seconds for o in valid_odds]) if valid_odds else 0.0

        return ReconciledMarketOdds(
            market=market,
            sport=sport,
            consensus_odds=consensus_odds,
            vig_free_probabilities=vig_free_probs,
            vig_free_odds=vig_free_odds,
            margin=round(margin, 4),
            freshness=sample.freshness,
            bookmaker_count=len(bookmakers),
            has_anomaly=has_anomaly,
            anomaly_reason="; ".join(anomaly_reasons) if anomaly_reasons else None,
            provider_sources=list(providers),
            raw_odds_count=len(valid_odds),
            odds_age_seconds=round(avg_age, 1),
        )


class ProviderRegistry:
    """
    Central registry for multi-provider gateway and health matrix generation.
    """

    def __init__(self):
        self._providers: Dict[str, BaseOddsProvider] = {}
        self._sports_providers: Dict[str, BaseSportsProvider] = {}

    def register_odds_provider(self, name: str, provider: BaseOddsProvider):
        self._providers[name] = provider
        logger.info(f"[ProviderRegistry] Registered odds provider: {name}")

    def register_sports_provider(self, name: str, provider: BaseSportsProvider):
        self._sports_providers[name] = provider
        logger.info(f"[ProviderRegistry] Registered sports provider: {name}")

    def get_odds_providers(self, sport: Optional[str] = None) -> List[BaseOddsProvider]:
        if not sport:
            return list(self._providers.values())
        sport_clean = sport.lower()
        return [
            p for p in self._providers.values()
            if sport_clean in [s.lower() for s in p.supported_sports()]
        ]

    async def fetch_reconciled_odds(
        self, fixture_id: str, sport: str = "football", market: str = "match_winner"
    ) -> Optional[ReconciledMarketOdds]:
        """Query all active providers supporting sport and reconcile their odds."""
        providers = self.get_odds_providers(sport)
        all_odds: List[NormalizedOdds] = []

        for p in providers:
            try:
                odds = await p.get_odds(fixture_id, sport)
                all_odds.extend(odds)
            except Exception as exc:
                logger.warning(f"[ProviderRegistry] Provider fetch error for {fixture_id}: {exc}")

        return OddsIntelligence.reconcile(all_odds, sport=sport, market=market)

    async def get_health_matrix(self) -> List[Dict[str, Any]]:
        """
        Generate Provider Health Matrix across all sports.
        Returns:
            List of dicts: [
                {"sport": "Football", "fixtures": True, "stats": True, "odds": True, "status": "Ready"},
                ...
            ]
        """
        sports_config = [
            {"sport": "Football", "key": "football", "fixtures": True, "stats": True},
            {"sport": "Basketball", "key": "basketball", "fixtures": True, "stats": True},
            {"sport": "Tennis", "key": "tennis", "fixtures": True, "stats": False},
            {"sport": "Baseball", "key": "baseball", "fixtures": True, "stats": False},
            {"sport": "Hockey", "key": "ice_hockey", "fixtures": True, "stats": False},
        ]

        matrix = []
        for s in sports_config:
            key = s["key"]
            odds_providers = self.get_odds_providers(key)
            has_odds = len(odds_providers) > 0

            # Determine overall status
            if s["fixtures"] and s["stats"] and has_odds:
                status = "Ready"
            elif s["fixtures"] and (s["stats"] or has_odds):
                status = "Limited"
            else:
                status = "Offline"

            matrix.append({
                "sport": s["sport"],
                "fixtures": s["fixtures"],
                "stats": s["stats"],
                "odds": has_odds,
                "status": status,
                "active_odds_providers": len(odds_providers),
            })
        return matrix


# Singleton Registry instance
default_provider_registry = ProviderRegistry()
