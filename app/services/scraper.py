# app/services/scraper.py
import asyncio
import random
import logging
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


# User-Agent rotation pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class InjuryScraper:
    """
    Scraper for injury news from sports websites.

    Features:
        - User-Agent rotation to avoid blocking
        - Retry logic with exponential backoff
        - Structured data extraction
        - Fallback selectors for site changes
    """

    def __init__(
        self,
        base_url: str = "https://www.premierinjuries.com",
        timeout: int = 5,
        max_retries: int = 3,
        use_playwright: bool = False
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_playwright = use_playwright

        # For Playwright (JavaScript-heavy sites)
        self.browser = None
        self.playwright = None

    def _get_headers(self) -> Dict[str, str]:
        """Get random headers for request"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def fetch_page(self, url: str) -> str:
        """Fetch a page with retry logic"""
        async with httpx.AsyncClient(
            headers=self._get_headers(),
            timeout=self.timeout,
            follow_redirects=True
        ) as client:
            logger.info(f"Fetching {url}")
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def fetch_injuries_premierleague(self) -> List[Dict]:
        """Fetch injuries from premierinjuries.com"""
        url = urljoin(self.base_url, "/injuries")

        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, "html.parser")

            injuries = []

            # Premier Injuries specific selectors
            injury_rows = soup.select("table.injury-table tbody tr")

            for row in injury_rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue

                player_name = cols[0].get_text(strip=True)
                team = cols[1].get_text(strip=True)
                injury = cols[2].get_text(strip=True)
                return_date = cols[3].get_text(strip=True) if len(cols) > 3 else "Unknown"

                injuries.append({
                    "player_name": player_name,
                    "team": team,
                    "injury": injury,
                    "return_date": return_date,
                    "status": self._normalize_status(injury),
                    "source": "premierinjuries",
                    "fetched_at": datetime.now().isoformat()
                })

            logger.info(f"Fetched {len(injuries)} injuries from Premier Injuries")
            return injuries

        except Exception as e:
            logger.error(f"Failed to fetch injuries: {e}")
            return []

    async def fetch_injuries_physioroom(self) -> List[Dict]:
        """Fetch injuries from physioroom.com"""
        url = "https://www.physioroom.com/news/english_premier_league_injuries.php"

        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, "html.parser")

            injuries = []

            # PhysioRoom selectors
            injury_table = soup.find("table", class_="injuries")
            if not injury_table:
                return []

            rows = injury_table.find_all("tr")

            for row in rows[1:]:  # Skip header
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                player_name = cols[0].get_text(strip=True)
                team = cols[1].get_text(strip=True)
                injury = cols[2].get_text(strip=True)
                return_date = cols[3].get_text(strip=True)
                status = cols[4].get_text(strip=True)

                injuries.append({
                    "player_name": player_name,
                    "team": team,
                    "injury": injury,
                    "return_date": return_date,
                    "status": self._normalize_status(injury + " " + status),
                    "source": "physioroom",
                    "fetched_at": datetime.now().isoformat()
                })

            logger.info(f"Fetched {len(injuries)} injuries from PhysioRoom")
            return injuries

        except Exception as e:
            logger.error(f"Failed to fetch PhysioRoom injuries: {e}")
            return []

    async def fetch_injuries_fantasyfootballfix(self) -> List[Dict]:
        """Fetch injuries from fantasyfootballfix.com"""
        url = "https://www.fantasyfootballfix.com/injury-news/"

        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, "html.parser")

            injuries = []

            # FantasyFootballFix selectors
            injury_cards = soup.select(".injury-card")

            for card in injury_cards:
                player_name = card.select_one(".player-name")
                team = card.select_one(".team-name")
                injury_text = card.select_one(".injury-text")

                if player_name:
                    injuries.append({
                        "player_name": player_name.get_text(strip=True),
                        "team": team.get_text(strip=True) if team else "Unknown",
                        "injury": injury_text.get_text(strip=True) if injury_text else "Unknown",
                        "return_date": "Unknown",
                        "status": self._normalize_status(injury_text.get_text(strip=True) if injury_text else ""),
                        "source": "fantasyfootballfix",
                        "fetched_at": datetime.now().isoformat()
                    })

            logger.info(f"Fetched {len(injuries)} injuries from FantasyFootballFix")
            return injuries

        except Exception as e:
            logger.error(f"Failed to fetch FantasyFootballFix injuries: {e}")
            return []

    async def fetch_injuries_transfermarkt(self, league: str = "premier-league") -> List[Dict]:
        """Fetch injuries from transfermarkt.com"""
        # Transfermarkt requires different approach - use their injury page
        url = f"https://www.transfermarkt.com/{league}/verletztespieler/wettbewerb/GB1"

        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, "html.parser")

            injuries = []

            # Transfermarkt selectors
            injury_table = soup.select("table.items")
            if not injury_table:
                return []

            rows = injury_table[0].find_all("tr", class_=["odd", "even"])

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 6:
                    continue

                player_name = cols[2].get_text(strip=True)
                team = cols[3].get_text(strip=True)
                injury = cols[4].get_text(strip=True)
                return_date = cols[5].get_text(strip=True)

                injuries.append({
                    "player_name": player_name,
                    "team": team,
                    "injury": injury,
                    "return_date": return_date,
                    "status": self._normalize_status(injury),
                    "source": "transfermarkt",
                    "fetched_at": datetime.now().isoformat()
                })

            logger.info(f"Fetched {len(injuries)} injuries from Transfermarkt")
            return injuries

        except Exception as e:
            logger.error(f"Failed to fetch Transfermarkt injuries: {e}")
            return []

    def _normalize_status(self, text: str) -> str:
        """Normalize injury status text"""
        text = text.lower()

        if any(word in text for word in ["out", "injured", "ruled out", "unavailable", "doubtful"]):
            if "doubtful" in text:
                return "doubtful"
            return "injured"
        elif any(word in text for word in ["questionable", "late fitness", "monitoring"]):
            return "questionable"
        elif any(word in text for word in ["return", "back in training", "light training"]):
            return "returning"
        else:
            return "fit"

    async def fetch_all_injuries(self) -> List[Dict]:
        """Fetch injuries from multiple sources and deduplicate"""
        tasks = [
            self.fetch_injuries_premierleague(),
            self.fetch_injuries_physioroom(),
            self.fetch_injuries_fantasyfootballfix(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_injuries = []
        seen_players = set()

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Scraper failed: {result}")
                continue

            for injury in result:
                player_key = f"{injury['player_name']}_{injury.get('team', '')}"
                if player_key not in seen_players:
                    seen_players.add(player_key)
                    all_injuries.append(injury)

        logger.info(f"Total unique injuries: {len(all_injuries)}")
        return all_injuries

    async def close(self):
        """Clean up resources"""
        if self.playwright:
            await self.playwright.stop()