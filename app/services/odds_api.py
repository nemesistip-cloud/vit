# app/services/odds_api.py
"""
Odds API Client - Real-time betting odds integration.

Supports:
- The Odds API (the-odds-api.com) - Free tier available
- Multiple bookmakers (Pinnacle, Bet365, etc.)
- Real-time odds streaming
- Odds movement tracking for CLV
"""

import asyncio
import httpx
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class OddsData:
    """Container for odds data"""
    match_id: str
    home_odds: float
    draw_odds: float
    away_odds: float
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    over_25_odds: Optional[float] = None
    under_25_odds: Optional[float] = None
    btts_yes_odds: Optional[float] = None
    btts_no_odds: Optional[float] = None
    bookmaker: str = "pinnacle"
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def implied_probabilities(self) -> Dict[str, float]:
        """Calculate implied probabilities (with vig)"""
        return {
            "home": 1 / self.home_odds if self.home_odds > 0 else 0.33,
            "draw": 1 / self.draw_odds if self.draw_odds > 0 else 0.33,
            "away": 1 / self.away_odds if self.away_odds > 0 else 0.33
        }

    def vig_free_probabilities(self) -> Dict[str, float]:
        """Calculate vig-free probabilities"""
        implied = self.implied_probabilities()
        total = sum(implied.values())
        if total <= 0:
            return {"home": 0.34, "draw": 0.33, "away": 0.33}
        return {k: v / total for k, v in implied.items()}

    def overround(self) -> float:
        """Calculate bookmaker margin"""
        implied = self.implied_probabilities()
        return sum(implied.values()) - 1.0


class OddsAPIClient:
    """
    Async client for The Odds API.

    Free tier: 500 requests/month
    Premium: 10,000+ requests/month

    Sports codes:
    - soccer_epl: English Premier League
    - soccer_uefa_champs_league: Champions League
    - soccer_la_liga: Spanish La Liga
    - soccer_serie_a: Italian Serie A
    - soccer_bundesliga: German Bundesliga
    - soccer_ligue_one: French Ligue 1
    """

    BASE_URL = "https://api.the-odds-api.com/v4"

    # Sport to competition mapping
    SPORT_MAPPING = {
        "premier_league": "soccer_epl",
        "la_liga": "soccer_la_liga",
        "serie_a": "soccer_serie_a",
        "bundesliga": "soccer_bundesliga",
        "ligue_1": "soccer_ligue_one",
        "championship": "soccer_efl_champ",
        "eredivisie": "soccer_eredivisie",
        "primeira_liga": "soccer_primeira_liga",
        "scottish_premiership": "soccer_scottish_premiership",
        "belgian_pro_league": "soccer_jupiler_pro_league",
        "champions_league": "soccer_uefa_champs_league",
        "europa_league": "soccer_uefa_europa_league",
    }

    # Preferred bookmakers (in order of reliability)
    PREFERRED_BOOKMAKERS = ["pinnacle", "bet365", "williamhill", "unibet", "betfair"]

    def __init__(
        self,
        api_key: str,
        timeout: int = 10,
        max_retries: int = 3,
        enable_cache: bool = True,
        cache_ttl: int = 60  # 1 minute for odds
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self.client = httpx.AsyncClient(timeout=self.timeout)

    def _get_cache_key(self, sport: str, regions: str, markets: str) -> str:
        """Generate cache key"""
        return f"{sport}:{regions}:{markets}"

    _key_invalid: bool = False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def _request(
        self,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make authenticated request to Odds API"""
        if self.__class__._key_invalid:
            logger.debug("Skipping odds API request — key is suspended")
            return {}
        params["apiKey"] = self.api_key

        try:
            response = await self.client.get(
                f"{self.BASE_URL}{endpoint}",
                params=params
            )

            # Track remaining requests (from headers)
            remaining = response.headers.get("x-requests-remaining")
            if remaining:
                logger.debug(f"API requests remaining: {remaining}")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code in (401, 403):
                logger.warning("Odds API key is invalid or expired — suspending all odds requests for this session")
                self.__class__._key_invalid = True
                return {}
            elif e.response is not None and e.response.status_code == 429:
                logger.warning("Odds API rate limit exceeded")
            raise

    async def get_sports(self) -> List[Dict]:
        """Get list of available sports"""
        data = await self._request("/sports", {})
        return data

    async def get_odds(
        self,
        sport: str = "soccer_epl",
        regions: str = "uk,us,eu",
        markets: str = "h2h,spreads,totals",
        odds_format: str = "decimal",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        Get current odds for matches.

        Args:
            sport: Sport key (e.g., "soccer_epl")
            regions: Comma-separated regions (uk, us, eu, au)
            markets: Comma-separated markets (h2h, spreads, totals)
            odds_format: "decimal" or "american"
            date_from: ISO date string
            date_to: ISO date string
            use_cache: Use cached response
        """
        if self.__class__._key_invalid:
            logger.debug(f"Skipping odds fetch for {sport} — API key is invalid")
            return []

        cache_key = self._get_cache_key(sport, regions, markets)

        if use_cache and self.enable_cache and cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                logger.debug(f"Cache hit for {sport}")
                return data

        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format
        }

        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to

        data = await self._request(f"/sports/{sport}/odds", params)

        if use_cache and self.enable_cache:
            self._cache[cache_key] = (data, datetime.now())

        return data

    async def get_odds_for_competition(
        self,
        competition: str,
        days_ahead: int = 3
    ) -> List[OddsData]:
        """
        Get odds for all matches in a competition.

        Args:
            competition: Competition name (e.g., "premier_league")
            days_ahead: How many days ahead to fetch
        """
        sport = self.SPORT_MAPPING.get(competition.lower(), "soccer_epl")

        date_from = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        date_to = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            raw_odds = await self.get_odds(
                sport=sport,
                date_from=date_from,
                date_to=date_to,
                use_cache=True
            )
        except Exception as e:
            logger.error(f"Failed to fetch odds: {e}")
            return []

        odds_list = []

        for match_odds in raw_odds:
            odds_data = self._extract_best_odds(match_odds)
            if odds_data:
                odds_list.append(odds_data)

        logger.info(f"Fetched odds for {len(odds_list)} matches in {competition}")
        return odds_list

    def _extract_best_odds(self, match_odds: Dict) -> Optional[OddsData]:
        """
        Extract best odds from available bookmakers.
        Uses preferred bookmakers in order, falls back to best available.
        """
        bookmakers = match_odds.get("bookmakers", [])

        if not bookmakers:
            return None

        # Try preferred bookmakers first
        for preferred in self.PREFERRED_BOOKMAKERS:
            for bookmaker in bookmakers:
                if bookmaker.get("key") == preferred:
                    odds_data = self._extract_from_bookmaker(match_odds, bookmaker)
                    if odds_data:
                        return odds_data

        # Fall back to best odds across all bookmakers
        best_home = 0
        best_draw = 0
        best_away = 0
        best_bookmaker = None

        home_key = str(match_odds.get("home_team", "")).strip().lower()
        away_key = str(match_odds.get("away_team", "")).strip().lower()

        for bookmaker in bookmakers:
            markets = bookmaker.get("markets", [])
            for market in markets:
                if market.get("key") == "h2h":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        name = str(outcome.get("name", "")).strip().lower()
                        odds = outcome.get("price", 0)
                        if name in ("home", home_key):
                            if odds > best_home:
                                best_home = odds
                        elif name == "draw":
                            if odds > best_draw:
                                best_draw = odds
                        elif name in ("away", away_key):
                            if odds > best_away:
                                best_away = odds

                    if best_home and best_draw and best_away:
                        best_bookmaker = bookmaker.get("key")
                        break

        if best_home and best_draw and best_away:
            return OddsData(
                match_id=str(match_odds.get("id")),
                home_odds=best_home,
                draw_odds=best_draw,
                away_odds=best_away,
                home_team=match_odds.get("home_team"),
                away_team=match_odds.get("away_team"),
                bookmaker=best_bookmaker or "best"
            )

        return None

    def _extract_from_bookmaker(
        self,
        match_odds: Dict,
        bookmaker: Dict
    ) -> Optional[OddsData]:
        """Extract odds from a specific bookmaker"""
        markets = bookmaker.get("markets", [])

        home_odds = None
        draw_odds = None
        away_odds = None
        over_25_odds = None
        under_25_odds = None
        btts_yes_odds = None
        btts_no_odds = None

        for market in markets:
            market_key = market.get("key")
            outcomes = market.get("outcomes", [])

            if market_key == "h2h":
                for outcome in outcomes:
                    name = outcome.get("name", "").lower()
                    price = outcome.get("price", 0)

                    if name == "home" or name == match_odds.get("home_team", "").lower():
                        home_odds = price
                    elif name == "draw":
                        draw_odds = price
                    elif name == "away" or name == match_odds.get("away_team", "").lower():
                        away_odds = price

            elif market_key == "totals" and market.get("point") == 2.5:
                for outcome in outcomes:
                    name = outcome.get("name", "").lower()
                    price = outcome.get("price", 0)

                    if name == "over":
                        over_25_odds = price
                    elif name == "under":
                        under_25_odds = price

            elif market_key == "btts":
                for outcome in outcomes:
                    name = outcome.get("name", "").lower()
                    price = outcome.get("price", 0)

                    if name == "yes":
                        btts_yes_odds = price
                    elif name == "no":
                        btts_no_odds = price

        if home_odds and draw_odds and away_odds:
            return OddsData(
                match_id=str(match_odds.get("id")),
                home_odds=home_odds,
                draw_odds=draw_odds,
                away_odds=away_odds,
                home_team=match_odds.get("home_team"),
                away_team=match_odds.get("away_team"),
                over_25_odds=over_25_odds,
                under_25_odds=under_25_odds,
                btts_yes_odds=btts_yes_odds,
                btts_no_odds=btts_no_odds,
                bookmaker=bookmaker.get("key", "unknown")
            )

        return None

    async def get_odds_movement(
        self,
        match_id: str,
        sport: str = "soccer_epl",
        hours_back: int = 24
    ) -> List[Dict]:
        """
        Track odds movement over time for CLV calculation.

        Note: This requires historical odds data which may require premium tier.
        """
        # This would typically query a database of historical odds
        # For now, return empty list (implement with database later)
        logger.warning(f"Odds movement tracking not fully implemented for {match_id}")
        return []

    async def get_sharp_odds(self, competition: str) -> List[OddsData]:
        """
        Get odds from sharp books only (Pinnacle, etc.)
        These are more efficient and indicate true market probability.
        """
        sport = self.SPORT_MAPPING.get(competition.lower(), "soccer_epl")

        try:
            raw_odds = await self.get_odds(
                sport=sport,
                regions="uk",
                markets="h2h",
                use_cache=True
            )
        except Exception as e:
            logger.error(f"Failed to fetch sharp odds: {e}")
            return []

        sharp_odds = []
        for match_odds in raw_odds:
            # Only use Pinnacle if available
            pinnacle_odds = None
            for bookmaker in match_odds.get("bookmakers", []):
                if bookmaker.get("key") == "pinnacle":
                    pinnacle_odds = self._extract_from_bookmaker(match_odds, bookmaker)
                    break

            if pinnacle_odds:
                sharp_odds.append(pinnacle_odds)

        return sharp_odds

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()