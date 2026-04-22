# app/pipelines/data_loader.py
import asyncio
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.services.football_api import FootballDataClient
from app.services.scraper import InjuryScraper
from app.services.odds_api import OddsAPIClient, OddsData

logger = logging.getLogger(__name__)


def normalize_team_name(name: str) -> str:
    if not name:
        return ""

    cleaned = name.lower().strip()
    cleaned = re.sub(r"\s+fc$", "", cleaned)
    cleaned = re.sub(r"\s+hotspur$", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned


@dataclass
class MatchContext:
    """Container for all data related to upcoming matches"""
    fixtures: List[Dict] = field(default_factory=list)
    standings: Dict = field(default_factory=dict)
    injuries: List[Dict] = field(default_factory=list)
    odds: List[OddsData] = field(default_factory=list)  # NEW: Odds data
    recent_form: Dict[str, List[Dict]] = field(default_factory=dict)
    head_to_head: Dict[str, List[Dict]] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "fixtures": self.fixtures,
            "standings": self.standings,
            "injuries": self.injuries,
            "odds": [o.__dict__ for o in self.odds] if self.odds else [],
            "recent_form": self.recent_form,
            "head_to_head": self.head_to_head
        }

    def is_empty(self) -> bool:
        return not self.fixtures and not self.standings


class DataLoader:
    """
    Async data loader for VIT Network.

    Features:
        - Parallel fetching from multiple sources
        - Caching to reduce API calls
        - Graceful degradation on failures
        - Team mapping to internal IDs
        - Odds API integration for market data
    """

    def __init__(
        self,
        api_key: str,
        odds_api_key: Optional[str] = None,
        injury_url: str = "https://www.premierinjuries.com",
        enable_scraping: bool = True,
        enable_odds: bool = True,
        cache_ttl: int = 300
    ):
        self.api_client = FootballDataClient(api_key, enable_cache=True)
        self.scraper = InjuryScraper(injury_url) if enable_scraping else None
        self.odds_client = OddsAPIClient(odds_api_key) if enable_odds and odds_api_key else None
        self.enable_scraping = enable_scraping
        self.enable_odds = enable_odds
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}

    async def fetch_all_context(
        self,
        competition: str,
        days_ahead: int = 7,
        include_recent_form: bool = True,
        include_h2h: bool = True,
        include_odds: bool = True
    ) -> MatchContext:
        """
        Fetch all context for upcoming matches in parallel.

        Args:
            competition: League name (e.g., "premier_league")
            days_ahead: How many days ahead to fetch fixtures
            include_recent_form: Include recent form data
            include_h2h: Include head-to-head history
            include_odds: Include odds data from API

        Returns:
            MatchContext with all fetched data
        """
        logger.info(f"Fetching context for {competition}")

        today = datetime.now().date()
        future = today + timedelta(days=days_ahead)

        # Build tasks for parallel execution
        tasks = {
            "fixtures": self.api_client.get_fixtures(
                competition,
                str(today),
                str(future)
            ),
            "standings": self.api_client.get_standings(competition)
        }

        # Add scraper tasks if enabled
        if self.enable_scraping and self.scraper:
            tasks["injuries"] = self.scraper.fetch_all_injuries()

        # Add odds tasks if enabled
        if self.enable_odds and self.odds_client and include_odds:
            tasks["odds"] = self.odds_client.get_odds_for_competition(competition, days_ahead)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Process results
        context = MatchContext()

        for task_name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {task_name}: {result}")
                continue

            if task_name == "fixtures":
                context.fixtures = result
            elif task_name == "standings":
                context.standings = result
            elif task_name == "injuries":
                context.injuries = result
            elif task_name == "odds":
                context.odds = result

        # Fetch additional data for each fixture (parallel)
        if include_recent_form or include_h2h:
            await self._enrich_context(context, include_recent_form, include_h2h)

        # Enrich fixtures with odds data
        if context.odds:
            context = self._enrich_fixtures_with_odds(context)

        logger.info(f"Context fetched: {len(context.fixtures)} fixtures, "
                   f"{len(context.injuries)} injuries, "
                   f"{len(context.odds)} odds entries")

        return context

    def _enrich_fixtures_with_odds(self, context: MatchContext) -> MatchContext:
        """Add odds data to fixtures"""
        # Build lookup dictionaries for odds by ID and by normalized team names
        odds_by_match = {}
        odds_by_names = {}
        for odds in context.odds:
            if odds.match_id:
                odds_by_match[odds.match_id] = odds

            if odds.home_team and odds.away_team:
                key = (
                    normalize_team_name(odds.home_team),
                    normalize_team_name(odds.away_team)
                )
                odds_by_names[key] = odds

        # Enrich each fixture
        for fixture in context.fixtures:
            external_id = str(fixture.get("external_id"))
            odds = odds_by_match.get(external_id)

            if not odds:
                fixture_key = (
                    normalize_team_name(fixture["home_team"]["name"]),
                    normalize_team_name(fixture["away_team"]["name"])
                )
                odds = odds_by_names.get(fixture_key) or odds_by_names.get((fixture_key[1], fixture_key[0]))

            if odds:
                fixture["odds"] = {
                    "home": odds.home_odds,
                    "draw": odds.draw_odds,
                    "away": odds.away_odds,
                    "over_25": odds.over_25_odds,
                    "under_25": odds.under_25_odds,
                    "btts_yes": odds.btts_yes_odds,
                    "btts_no": odds.btts_no_odds,
                    "bookmaker": odds.bookmaker,
                    "vig_free_probs": odds.vig_free_probabilities(),
                    "overround": odds.overround(),
                    "timestamp": odds.timestamp.isoformat() if odds.timestamp else None
                }

        return context

    async def _enrich_context(
        self,
        context: MatchContext,
        include_recent_form: bool,
        include_h2h: bool
    ):
        """Enrich context with recent form and H2H data"""
        if not context.fixtures:
            return

        # Collect unique teams
        teams = set()
        for fixture in context.fixtures:
            home = fixture.get("home_team", {})
            away = fixture.get("away_team", {})
            if home.get("external_id"):
                teams.add(home["external_id"])
            if away.get("external_id"):
                teams.add(away["external_id"])

        # Fetch recent form for each team
        if include_recent_form:
            form_tasks = []
            for team_id in teams:
                form_tasks.append(
                    self.api_client.get_team_matches(int(team_id), limit=10)
                )

            form_results = await asyncio.gather(*form_tasks, return_exceptions=True)

            for team_id, result in zip(teams, form_results):
                if not isinstance(result, Exception):
                    context.recent_form[team_id] = result

        # Fetch H2H for each fixture
        if include_h2h:
            h2h_tasks = []
            for fixture in context.fixtures:
                home_id = fixture.get("home_team", {}).get("external_id")
                away_id = fixture.get("away_team", {}).get("external_id")
                if home_id and away_id:
                    h2h_tasks.append(
                        self.api_client.get_head_to_head(int(home_id), int(away_id), limit=5)
                    )
                else:
                    async def _empty_h2h():
                        return []
                    h2h_tasks.append(_empty_h2h())

            h2h_results = await asyncio.gather(*h2h_tasks, return_exceptions=True)

            for fixture, result in zip(context.fixtures, h2h_results):
                if not isinstance(result, Exception):
                    key = f"{fixture.get('home_team', {}).get('name')}_vs_{fixture.get('away_team', {}).get('name')}"
                    context.head_to_head[key] = result

    async def fetch_historical_matches(
        self,
        competition: str,
        days_back: int = 90,
        limit: int = 500
    ) -> List[Dict]:
        """Fetch historical matches for training"""
        logger.info(f"Fetching historical matches for {competition} ({days_back} days)")

        date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")

        return await self.api_client.get_finished_matches(
            competition,
            date_from,
            date_to,
            limit
        )

    async def fetch_odds_only(
        self,
        competition: str,
        days_ahead: int = 3
    ) -> List[OddsData]:
        """Fetch only odds data (lightweight)"""
        if not self.odds_client:
            logger.warning("Odds client not initialized")
            return []

        return await self.odds_client.get_odds_for_competition(competition, days_ahead)

    async def fetch_sharp_odds_only(
        self,
        competition: str
    ) -> List[OddsData]:
        """Fetch sharp odds only (Pinnacle)"""
        if not self.odds_client:
            logger.warning("Odds client not initialized")
            return []

        return await self.odds_client.get_sharp_odds(competition)

    async def get_team_info(self, team_name: str) -> Optional[Dict]:
        """Get team information by name (fuzzy search)"""
        # This would ideally use a team mapping table
        # For now, return None and let caller handle
        return None

    async def close(self):
        """Close all connections"""
        await self.api_client.close()
        if self.scraper:
            await self.scraper.close()
        if self.odds_client:
            await self.odds_client.close()