# app/services/football_api.py
import asyncio
import httpx
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from functools import wraps
import hashlib
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

logger = logging.getLogger(__name__)


def rate_limit_backoff(func):
    """Decorator for rate limit handling with exponential backoff"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return await func(self, *args, **kwargs)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait_time = self.base_backoff ** attempt
                    logger.warning(f"Rate limited. Retrying in {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error ({type(e).__name__}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.base_backoff ** attempt
                await asyncio.sleep(wait_time)
        raise Exception(f"Max retries ({self.max_retries}) exceeded")
    return wrapper


class FootballDataClient:
    """
    Async client for football-data.org API.

    Features:
        - Rate limit handling with exponential backoff
        - Team mapping to internal UUIDs
        - Response caching
        - Clean error handling
        - Circuit breaker: suspends all requests after a 401/403
    """

    _key_forbidden: bool = False          # class-level: suspended after 401/403
    _consecutive_timeouts: int = 0        # class-level: timeout counter
    _timeout_circuit_open: bool = False   # class-level: skip after repeated timeouts
    _TIMEOUT_THRESHOLD: int = 3           # open circuit after this many consecutive timeouts
    _rate_limited_until: float = 0.0      # class-level: epoch time until which 429 suspends requests

    BASE_URL = "https://api.football-data.org/v4"

    # Competition codes mapping
    # Free-tier competitions (12 total on football-data.org free plan)
    FREE_TIER_CODES = ["PL", "ELC", "BL1", "SA", "PD", "FL1", "DED", "PPL", "BSA", "CL", "EC", "WC"]

    COMPETITIONS = {
        # Free-tier leagues
        "premier_league":       "PL",
        "championship":         "ELC",
        "bundesliga":           "BL1",
        "serie_a":              "SA",
        "la_liga":              "PD",
        "ligue_1":              "FL1",
        "eredivisie":           "DED",
        "primeira_liga":        "PPL",
        "brasileirao":          "BSA",
        "brazil_serie_a":       "BSA",
        "champions_league":     "CL",
        "ucl":                  "CL",
        "euro_championship":    "EC",
        "european_championship":"EC",
        "euros":                "EC",
        "world_cup":            "WC",
        "fifa_world_cup":       "WC",
        # Additional paid-tier (fall back gracefully via 400 handler)
        "uel":                  "EL",
        "europa_league":        "EL",
        "conference_league":    "ECL",
        "scottish_premiership": "SPL",
        "belgian_pro_league":   "BJL",
        "super_lig":            "TR1",
        "mls":                  "MLS",
    }

    def __init__(
        self,
        api_key: str,
        timeout: int = 5,
        max_retries: int = 2,
        base_backoff: float = 1.0,
        enable_cache: bool = True
    ):
        self.api_key = api_key
        self.headers = {"X-Auth-Token": api_key}
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.enable_cache = enable_cache
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._team_mapping: Dict[str, str] = {}  # external_id -> internal_uuid
        self.client = httpx.AsyncClient(timeout=self.timeout, headers=self.headers)

    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from endpoint and params"""
        key_str = endpoint
        if params:
            key_str += str(sorted(params.items()))
        return hashlib.md5(key_str.encode()).hexdigest()

    async def _cached_request(self, endpoint: str, params: Optional[Dict] = None, ttl: int = 300) -> Dict:
        """Make request with caching"""
        if self.__class__._key_forbidden:
            logger.debug(f"Skipping football API request for {endpoint} — key is forbidden")
            return {}
        if self.__class__._timeout_circuit_open:
            logger.debug(f"Skipping football API request for {endpoint} — host unreachable")
            return {}

        cache_key = self._get_cache_key(endpoint, params)

        if self.enable_cache and cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < ttl:
                logger.debug(f"Cache hit for {endpoint}")
                return data

        data = await self._request(endpoint, params)

        if self.enable_cache and data:
            self._cache[cache_key] = (data, datetime.now())

        return data

    @rate_limit_backoff
    async def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make authenticated request to football-data.org"""
        import time as _time
        if self.__class__._key_forbidden or self.__class__._timeout_circuit_open:
            return {}
        if self.__class__._rate_limited_until > _time.time():
            logger.debug("Football Data API suspended due to rate limit — skipping request")
            return {}

        url = f"{self.BASE_URL}{endpoint}"

        logger.debug(f"Requesting {url} with params {params}")

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            # Reset timeout counter on success
            self.__class__._consecutive_timeouts = 0
            return response.json()

        except (httpx.ConnectTimeout, httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as e:
            self.__class__._consecutive_timeouts += 1
            if self.__class__._consecutive_timeouts >= self.__class__._TIMEOUT_THRESHOLD:
                self.__class__._timeout_circuit_open = True
                logger.warning(
                    "Football Data API is unreachable after %d consecutive errors — "
                    "suspending requests for this session. The host may be blocking this environment.",
                    self.__class__._consecutive_timeouts,
                )
            else:
                logger.warning(
                    "Football Data API connection error (%s) — attempt %d/%d",
                    type(e).__name__, self.__class__._consecutive_timeouts, self.__class__._TIMEOUT_THRESHOLD,
                )
            return {}

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                self.__class__._key_forbidden = True
                logger.warning(
                    "Football Data API key is forbidden/invalid — suspending all requests for this session. "
                    "Renew your API subscription at football-data.org to restore live data."
                )
                return {}
            elif e.response.status_code == 400:
                logger.debug(
                    "Football Data API returned 400 for %s — competition may not be "
                    "available on this API tier; skipping.",
                    endpoint,
                )
                return {}
            elif e.response.status_code == 404:
                logger.warning(f"Endpoint not found: {endpoint}")
                return {}
            elif e.response.status_code == 429:
                import time as _time
                self.__class__._rate_limited_until = _time.time() + 60
                logger.warning(
                    "Football Data API rate limit hit — suspending requests for 60 seconds"
                )
                return {}
            raise

    async def get_competition_id(self, competition_name: str) -> Optional[str]:
        """Get competition code from name"""
        return self.COMPETITIONS.get(competition_name.lower())

    async def get_fixtures(
        self,
        competition: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: str = "SCHEDULED"
    ) -> List[Dict]:
        """
        Get fixtures for a competition.

        Args:
            competition: Competition name or code
            date_from: ISO date string (YYYY-MM-DD)
            date_to: ISO date string (YYYY-MM-DD)
            status: Match status (SCHEDULED, FINISHED, etc.)
        """
        # Get competition code
        comp_code = await self.get_competition_id(competition)
        if not comp_code:
            logger.warning(f"Unknown competition: {competition}, using as-is")
            comp_code = competition

        # Default date range (next 7 days)
        if not date_from:
            date_from = datetime.now().strftime("%Y-%m-%d")
        if not date_to:
            date_to = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        params = {
            "competitions": comp_code,
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": status,
            "limit": 50
        }

        data = await self._cached_request("/matches", params, ttl=300)

        matches = data.get("matches", [])

        return [self._map_match(m) for m in matches]

    async def get_finished_matches(
        self,
        competition: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get finished matches for training"""
        if not date_from:
            date_from = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")

        comp_code = await self.get_competition_id(competition) or competition

        params = {
            "competitions": comp_code,
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": "FINISHED",
            "limit": limit
        }

        data = await self._cached_request("/matches", params, ttl=3600)

        matches = data.get("matches", [])

        return [self._map_match_with_result(m) for m in matches]

    async def get_standings(self, competition: str) -> Dict:
        """Get league standings"""
        comp_code = await self.get_competition_id(competition) or competition

        data = await self._cached_request(f"/competitions/{comp_code}/standings", ttl=3600)

        standings = data.get("standings", [])

        if standings:
            return self._map_standings(standings[0])

        return {}

    async def get_team(self, team_id: int) -> Dict:
        """Get team details"""
        data = await self._cached_request(f"/teams/{team_id}", ttl=86400)
        return self._map_team(data)

    async def get_team_matches(
        self,
        team_id: int,
        limit: int = 10,
        status: str = "FINISHED"
    ) -> List[Dict]:
        """Get recent matches for a team"""
        params = {"limit": limit, "status": status}
        data = await self._cached_request(f"/teams/{team_id}/matches", params, ttl=3600)

        matches = data.get("matches", [])
        return [self._map_match(m) for m in matches]

    async def get_head_to_head(self, team1_id: int, team2_id: int, limit: int = 10) -> List[Dict]:
        """Get head-to-head history between two teams"""
        params = {"limit": limit}
        data = await self._cached_request(f"/teams/{team1_id}/matches", params, ttl=86400)

        matches = data.get("matches", [])

        # Filter matches against team2
        h2h = []
        for match in matches:
            opponent_id = match.get("awayTeam", {}).get("id")
            if match.get("homeTeam", {}).get("id") == team2_id:
                opponent_id = match.get("homeTeam", {}).get("id")

            if opponent_id == team2_id:
                h2h.append(self._map_match_with_result(match))

        return h2h[:limit]

    def _map_match(self, match: Dict) -> Dict:
        """Map API match to internal format (without results)"""
        return {
            "external_id": match["id"],
            "home_team": self._map_team(match["homeTeam"]),
            "away_team": self._map_team(match["awayTeam"]),
            "kickoff_time": match["utcDate"],
            "status": match["status"],
            "competition": match.get("competition", {}).get("name"),
            "matchday": match.get("matchday")
        }

    def _map_match_with_result(self, match: Dict) -> Dict:
        """Map API match to internal format with results"""
        base = self._map_match(match)

        score = match.get("score", {})
        full_time = score.get("fullTime", {})

        base["home_goals"] = full_time.get("home")
        base["away_goals"] = full_time.get("away")
        base["half_time_home"] = score.get("halfTime", {}).get("home")
        base["half_time_away"] = score.get("halfTime", {}).get("away")

        return base

    def _map_team(self, team: Dict) -> Dict:
        """Map API team to internal format"""
        external_id = str(team["id"])

        return {
            "external_id": external_id,
            "name": team["name"],
            "short_name": team.get("shortName", team["name"]),
            "tla": team.get("tla"),
            "crest_url": team.get("crest")
        }

    def _map_standings(self, standing: Dict) -> Dict:
        """Map API standings to internal format"""
        table = []
        for entry in standing.get("table", []):
            team = entry.get("team", {})
            table.append({
                "position": entry.get("position"),
                "team": self._map_team(team),
                "played_games": entry.get("playedGames"),
                "won": entry.get("won"),
                "draw": entry.get("draw"),
                "lost": entry.get("lost"),
                "points": entry.get("points"),
                "goals_for": entry.get("goalsFor"),
                "goals_against": entry.get("goalsAgainst"),
                "goal_difference": entry.get("goalDifference"),
                "form": entry.get("form")
            })

        return {
            "stage": standing.get("stage"),
            "type": standing.get("type"),
            "table": table
        }

    async def map_to_internal_team_id(self, external_id: str) -> Optional[str]:
        """Map external team ID to internal UUID.

        First checks the in-memory cache, then queries the Team table in the DB.
        Falls back to returning the external_id unchanged when no mapping is found.
        """
        if external_id in self._team_mapping:
            return self._team_mapping[external_id]

        try:
            from app.db.database import AsyncSessionLocal
            from app.db.models import Team
            from sqlalchemy import select as _select

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    _select(Team).where(Team.external_id == str(external_id))
                )
                team = result.scalar_one_or_none()
                if team:
                    # Cache the mapping for subsequent calls in this service instance
                    self._team_mapping[external_id] = str(team.id)
                    return str(team.id)
        except Exception as _e:
            logger.debug(f"DB team mapping lookup failed for external_id={external_id}: {_e}")

        # No mapping found — return the external ID unchanged
        return external_id

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()