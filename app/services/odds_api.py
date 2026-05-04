# app/services/odds_api.py
"""
Odds API Client - Real-time betting odds integration.

Supports:
- The Odds API (the-odds-api.com) - Free tier available
- Multiple bookmakers (Pinnacle, Bet365, etc.)
- Real-time odds streaming
- Odds movement tracking for CLV

Markets fetched from API:
  h2h      → 1X2 (home / draw / away)
  totals   → Over/Under goals at 1.5, 2.5, 3.5, 4.5
  spreads  → Asian Handicap (all available lines)

Markets derived mathematically:
  double_chance  → 1X, X2, 12  (from h2h vig-free probs)
  draw_no_bet    → DNB Home / DNB Away (from h2h vig-free probs)
"""

import asyncio
import httpx
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class OddsData:
    """Container for full-market odds data from a single event / bookmaker."""

    # ── Identity ────────────────────────────────────────────────────────
    match_id:   str
    home_team:  Optional[str] = None
    away_team:  Optional[str] = None
    bookmaker:  str            = "pinnacle"
    timestamp:  datetime       = None

    # ── 1X2 / h2h ───────────────────────────────────────────────────────
    home_odds:  float          = 0.0
    draw_odds:  float          = 0.0
    away_odds:  float          = 0.0

    # ── Over / Under  (totals market at various lines) ───────────────────
    over_15_odds:  Optional[float] = None
    under_15_odds: Optional[float] = None
    over_25_odds:  Optional[float] = None
    under_25_odds: Optional[float] = None
    over_35_odds:  Optional[float] = None
    under_35_odds: Optional[float] = None
    over_45_odds:  Optional[float] = None
    under_45_odds: Optional[float] = None

    # ── Asian Handicap (spreads market) ─────────────────────────────────
    ah_line:      Optional[float]      = None   # primary / fairest line
    ah_home_odds: Optional[float]      = None
    ah_away_odds: Optional[float]      = None
    ah_lines:     List[Dict]           = field(default_factory=list)
    # [{line: -1.5, home_odds: 1.87, away_odds: 2.05}, …]

    # ── Derived: Double Chance ────────────────────────────────────────────
    # Calculated from vig-free 1X2 probabilities
    dc_1x_odds: Optional[float] = None   # Home or Draw
    dc_x2_odds: Optional[float] = None   # Draw or Away
    dc_12_odds: Optional[float] = None   # Home or Away

    # ── Derived: Draw No Bet ─────────────────────────────────────────────
    dnb_home_odds: Optional[float] = None
    dnb_away_odds: Optional[float] = None

    # ── Legacy alias kept for backward compat ───────────────────────────
    btts_yes_odds: Optional[float] = None
    btts_no_odds:  Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    # ────────────────────────────────────────────────────────────────────
    # Probability helpers
    # ────────────────────────────────────────────────────────────────────

    def implied_probabilities(self) -> Dict[str, float]:
        """Raw implied probabilities (include bookmaker vig)."""
        return {
            "home": 1 / self.home_odds if self.home_odds > 1 else 0.333,
            "draw": 1 / self.draw_odds if self.draw_odds > 1 else 0.333,
            "away": 1 / self.away_odds if self.away_odds > 1 else 0.333,
        }

    def vig_free_probabilities(self) -> Dict[str, float]:
        """Vig-free (sharp) probabilities — sum to 1.0."""
        raw = self.implied_probabilities()
        total = sum(raw.values())
        if total <= 0:
            return {"home": 0.34, "draw": 0.33, "away": 0.33}
        return {k: v / total for k, v in raw.items()}

    def overround(self) -> float:
        """Bookmaker margin (vig). 0.05 = 5% margin."""
        return sum(self.implied_probabilities().values()) - 1.0

    def to_snapshot(self) -> Dict[str, Any]:
        """Serialisable dict for storing in the odds_snapshot JSON column."""
        vf = self.vig_free_probabilities()
        snap: Dict[str, Any] = {
            "home":          self.home_odds,
            "draw":          self.draw_odds,
            "away":          self.away_odds,
            "bookmaker":     self.bookmaker,
            "overround":     round(self.overround(), 5),
            "vig_free_probs": vf,
        }
        # Over / Under lines
        for attr, key in [
            ("over_15_odds",  "over_15"),
            ("under_15_odds", "under_15"),
            ("over_25_odds",  "over_25"),
            ("under_25_odds", "under_25"),
            ("over_35_odds",  "over_35"),
            ("under_35_odds", "under_35"),
            ("over_45_odds",  "over_45"),
            ("under_45_odds", "under_45"),
        ]:
            val = getattr(self, attr)
            if val:
                snap[key] = val

        # Asian Handicap
        if self.ah_line is not None:
            snap["ah_line"]      = self.ah_line
            snap["ah_home_odds"] = self.ah_home_odds
            snap["ah_away_odds"] = self.ah_away_odds
        if self.ah_lines:
            snap["ah_lines"] = self.ah_lines

        # Derived markets
        for attr, key in [
            ("dc_1x_odds",     "dc_1x"),
            ("dc_x2_odds",     "dc_x2"),
            ("dc_12_odds",     "dc_12"),
            ("dnb_home_odds",  "dnb_home"),
            ("dnb_away_odds",  "dnb_away"),
        ]:
            val = getattr(self, attr)
            if val:
                snap[key] = val

        return snap


# ── Helpers ───────────────────────────────────────────────────────────

def _vig_free_odds(p1: float, p2: float) -> float:
    """Convert two raw implied probabilities to a fair combined odds."""
    total = p1 + p2
    if total <= 0:
        return 0.0
    fair_p = (p1 / total + p2 / total) / 2 * 2  # = (p1+p2)/total  — actually just renorm
    fair_p = (p1 + p2)                            # sum of the two implied probs
    # The fair odds for an either/or = 1 / (vf_p1 + vf_p2)
    # where vf_pi = pi / (p1+p2+p3) — but we don't have p3 here.
    # Caller passes already-vf probs, so just sum and invert.
    return round(1 / fair_p, 3) if fair_p > 0 else 0.0


def _derive_markets(odds: OddsData) -> None:
    """
    Fill in Double Chance and Draw No Bet from h2h vig-free probabilities.
    Modifies the OddsData object in-place.
    """
    if not (odds.home_odds > 1 and odds.draw_odds > 1 and odds.away_odds > 1):
        return

    # Raw implied probabilities (with vig)
    ph = 1 / odds.home_odds
    pd = 1 / odds.draw_odds
    pa = 1 / odds.away_odds
    total = ph + pd + pa
    if total <= 0:
        return

    # Vig-free probs (sharp / no-vig)
    vph = ph / total
    vpd = pd / total
    vpa = pa / total

    # ── Double Chance ──────────────────────────────────────────────────
    # 1X  = P(home) + P(draw)
    # X2  = P(draw) + P(away)
    # 12  = P(home) + P(away)
    def _dc_odds(p_sum: float) -> Optional[float]:
        if p_sum <= 0 or p_sum >= 1:
            return None
        return round(1 / p_sum, 3)

    odds.dc_1x_odds = _dc_odds(vph + vpd)
    odds.dc_x2_odds = _dc_odds(vpd + vpa)
    odds.dc_12_odds = _dc_odds(vph + vpa)

    # ── Draw No Bet ─────────────────────────────────────────────────────
    # Remove draw; renormalise home vs away
    dn_total = vph + vpa
    if dn_total > 0:
        odds.dnb_home_odds = round(1 / (vph / dn_total), 3)
        odds.dnb_away_odds = round(1 / (vpa / dn_total), 3)


# ═════════════════════════════════════════════════════════════════════
class OddsAPIClient:
    """
    Async client for The Odds API v4 — fetches h2h, totals, and spreads
    for all supported soccer competitions.

    Free tier: 500 requests/month
    Premium:   10 000+ requests/month

    Markets fetched per call: h2h,totals,spreads  (3 markets in one request)
    Derived on the fly:       double_chance, draw_no_bet
    """

    BASE_URL = "https://api.the-odds-api.com/v4"

    # ── Comprehensive sport key mapping ──────────────────────────────
    SPORT_MAPPING: Dict[str, str] = {
        # Big 5 + UK
        "premier_league":           "soccer_epl",
        "epl":                      "soccer_epl",
        "la_liga":                  "soccer_spain_la_liga",
        "spain_la_liga":            "soccer_spain_la_liga",
        "serie_a":                  "soccer_italy_serie_a",
        "italy_serie_a":            "soccer_italy_serie_a",
        "bundesliga":               "soccer_germany_bundesliga",
        "germany_bundesliga":       "soccer_germany_bundesliga",
        "ligue_1":                  "soccer_france_ligue_one",
        "ligue1":                   "soccer_france_ligue_one",
        "france_ligue_one":         "soccer_france_ligue_one",
        "championship":             "soccer_efl_champ",
        "efl_championship":         "soccer_efl_champ",
        "league_1":                 "soccer_england_league1",
        "league_2":                 "soccer_england_league2",
        "fa_cup":                   "soccer_fa_cup",
        "scottish_premiership":     "soccer_scotland_premiership",
        # Europe
        "champions_league":         "soccer_uefa_champs_league",
        "ucl":                      "soccer_uefa_champs_league",
        "europa_league":            "soccer_uefa_europa_league",
        "uel":                      "soccer_uefa_europa_league",
        "eredivisie":               "soccer_eredivisie",
        "netherlands_eredivisie":   "soccer_eredivisie",
        "primeira_liga":            "soccer_primeira_liga",
        "portugal_primeira_liga":   "soccer_primeira_liga",
        "belgian_pro_league":       "soccer_belgium_first_div",
        "jupiler_pro_league":       "soccer_belgium_first_div",
        "austria_bundesliga":       "soccer_austria_bundesliga",
        "denmark_superliga":        "soccer_denmark_superliga",
        "finland_veikkausliiga":    "soccer_finland_veikkausliiga",
        "greece_super_league":      "soccer_greece_super_league",
        "germany_bundesliga2":      "soccer_germany_bundesliga2",
        "germany_liga3":            "soccer_germany_liga3",
        "germany_dfb_pokal":        "soccer_germany_dfb_pokal",
        "spain_segunda":            "soccer_spain_segunda_division",
        "italy_serie_b":            "soccer_italy_serie_b",
        "france_ligue_2":           "soccer_france_ligue_two",
        # Americas
        "mls":                      "soccer_usa_mls",
        "usa_mls":                  "soccer_usa_mls",
        "brazil_serie_a":           "soccer_brazil_campeonato",
        "brazil_serie_b":           "soccer_brazil_serie_b",
        "argentina_primera":        "soccer_argentina_primera_division",
        "chile_primera":            "soccer_chile_campeonato",
        "copa_libertadores":        "soccer_conmebol_copa_libertadores",
        "copa_sudamericana":        "soccer_conmebol_copa_sudamericana",
        # Asia / Oceania
        "australia_aleague":        "soccer_australia_aleague",
        "china_super_league":       "soccer_china_superleague",
        # World
        "world_cup":                "soccer_fifa_world_cup",
    }

    # Preferred bookmakers in reliability order
    PREFERRED_BOOKMAKERS = [
        "pinnacle", "bet365", "williamhill", "unibet", "betfair_ex_eu",
        "betway", "bwin", "unibet_eu",
    ]

    # Markets to request from API (btts not available for soccer on standard endpoint)
    FETCH_MARKETS = "h2h,totals,spreads"

    def __init__(
        self,
        api_key: str,
        timeout: int = 12,
        max_retries: int = 3,
        enable_cache: bool = True,
        cache_ttl: int = 90,          # 90 seconds for live odds
        regions: str = "eu,uk",
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.regions = regions
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self.client = httpx.AsyncClient(timeout=self.timeout)

    # ── internal helpers ─────────────────────────────────────────────

    def _get_cache_key(self, sport: str, regions: str, markets: str) -> str:
        return f"{sport}:{regions}:{markets}"

    _key_invalid: bool = False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _request(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """Make authenticated request to Odds API."""
        if self.__class__._key_invalid:
            logger.debug("Skipping odds API request — key is suspended")
            return {}
        params["apiKey"] = self.api_key

        try:
            response = await self.client.get(
                f"{self.BASE_URL}{endpoint}",
                params=params,
            )
            remaining = response.headers.get("x-requests-remaining")
            if remaining:
                logger.debug(f"Odds API requests remaining: {remaining}")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code in (401, 403):
                logger.warning(
                    "Odds API key invalid or expired — suspending requests for this session"
                )
                self.__class__._key_invalid = True
                return {}
            elif e.response is not None and e.response.status_code == 402:
                logger.warning("Odds API quota exhausted")
                self.__class__._key_invalid = True
                return {}
            elif e.response is not None and e.response.status_code == 429:
                logger.warning("Odds API rate limit exceeded")
            raise

    # ── Public API ───────────────────────────────────────────────────

    async def get_sports(self) -> List[Dict]:
        """Get list of available sports / competitions."""
        return await self._request("/sports", {})

    async def get_odds(
        self,
        sport: str          = "soccer_epl",
        regions: str        = None,
        markets: str        = None,
        odds_format: str    = "decimal",
        date_from: Optional[str] = None,
        date_to:   Optional[str] = None,
        use_cache: bool     = True,
    ) -> List[Dict]:
        """
        Fetch raw event odds from the API.

        markets defaults to ``FETCH_MARKETS`` (h2h,totals,spreads).
        """
        if self.__class__._key_invalid:
            logger.debug(f"Skipping odds fetch for {sport} — API key invalid/quota exceeded")
            return []

        markets = markets or self.FETCH_MARKETS
        regions = regions or self.regions

        cache_key = self._get_cache_key(sport, regions, markets)
        if use_cache and self.enable_cache and cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if (datetime.now() - ts).seconds < self.cache_ttl:
                logger.debug(f"Odds cache hit: {sport}")
                return data

        params: Dict[str, Any] = {
            "regions":    regions,
            "markets":    markets,
            "oddsFormat": odds_format,
        }
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to

        data = await self._request(f"/sports/{sport}/odds", params)
        if not isinstance(data, list):
            data = []

        if use_cache and self.enable_cache:
            self._cache[cache_key] = (data, datetime.now())

        return data

    async def get_odds_for_competition(
        self,
        competition: str,
        days_ahead: int = 3,
    ) -> List["OddsData"]:
        """
        Return a list of ``OddsData`` objects (one per event) for a competition.
        All markets are fetched and derived in a single API call.
        """
        sport = self.SPORT_MAPPING.get(competition.lower(), "soccer_epl")
        date_from = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        date_to   = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            raw_odds = await self.get_odds(
                sport=sport,
                date_from=date_from,
                date_to=date_to,
                use_cache=True,
            )
        except Exception as e:
            logger.error(f"Failed to fetch odds for {competition}: {e}")
            return []

        result = []
        for event in raw_odds:
            od = self._extract_best_odds(event)
            if od:
                result.append(od)

        logger.info(f"Fetched full-market odds for {len(result)} matches in {competition}")
        return result

    async def get_all_markets_for_event(
        self,
        sport: str,
        event_id: str,
    ) -> Optional[Dict]:
        """
        Fetch all markets for a single event by its Odds API event_id.
        Returns a raw dict with all bookmakers and markets, or None on failure.
        """
        if self.__class__._key_invalid:
            return None
        try:
            params: Dict[str, Any] = {
                "apiKey":     self.api_key,
                "regions":    self.regions,
                "markets":    self.FETCH_MARKETS,
                "oddsFormat": "decimal",
            }
            resp = await self.client.get(
                f"{self.BASE_URL}/sports/{sport}/events/{event_id}/odds",
                params=params,
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.warning(f"Event odds fetch failed for {event_id}: {e}")
            return None

    async def get_sharp_odds(self, competition: str) -> List["OddsData"]:
        """Return Pinnacle-only odds (sharp-book proxy) for a competition."""
        sport = self.SPORT_MAPPING.get(competition.lower(), "soccer_epl")
        try:
            raw_odds = await self.get_odds(sport=sport, markets="h2h,totals,spreads", use_cache=True)
        except Exception as e:
            logger.error(f"Failed to fetch sharp odds: {e}")
            return []

        sharp = []
        for event in raw_odds:
            for bk in event.get("bookmakers", []):
                if bk.get("key") == "pinnacle":
                    od = self._extract_from_bookmaker(event, bk)
                    if od:
                        sharp.append(od)
                    break
        return sharp

    # ── Extraction helpers ──────────────────────────────────────────

    def _extract_best_odds(self, event: Dict) -> Optional["OddsData"]:
        """
        Extract the best available odds from the event across all bookmakers.
        Preferred bookmakers are tried first; falls back to best-price composite.
        """
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            return None

        bk_map = {bk["key"]: bk for bk in bookmakers}

        # 1. Try preferred bookmakers in order
        for preferred in self.PREFERRED_BOOKMAKERS:
            if preferred in bk_map:
                od = self._extract_from_bookmaker(event, bk_map[preferred])
                if od and od.home_odds > 1:
                    return od

        # 2. Fall back: best price per outcome across all bookmakers
        return self._extract_best_composite(event, bookmakers)

    def _extract_from_bookmaker(
        self,
        event: Dict,
        bookmaker: Dict,
    ) -> Optional["OddsData"]:
        """
        Extract ALL market odds from a single bookmaker's data block.

        Parses: h2h, totals (1.5/2.5/3.5/4.5), spreads (all AH lines).
        Derives: double_chance, draw_no_bet.
        """
        home_name = str(event.get("home_team", "")).strip()
        away_name = str(event.get("away_team", "")).strip()

        od = OddsData(
            match_id   = str(event.get("id", "")),
            home_team  = home_name,
            away_team  = away_name,
            bookmaker  = bookmaker.get("key", "unknown"),
        )

        ah_lines_raw: Dict[float, Dict[str, float]] = {}  # line → {home, away}

        for market in bookmaker.get("markets", []):
            mk  = market.get("key", "")
            pts = market.get("point")           # numeric line if present at market level
            ocs = market.get("outcomes", [])

            # ── 1X2 ────────────────────────────────────────────────
            if mk == "h2h":
                for o in ocs:
                    name  = str(o.get("name", "")).strip()
                    price = float(o.get("price", 0) or 0)
                    nl    = name.lower()
                    if nl in ("home", home_name.lower()):
                        od.home_odds = price
                    elif nl == "draw":
                        od.draw_odds = price
                    elif nl in ("away", away_name.lower()):
                        od.away_odds = price

            # ── Over / Under  (multiple lines) ─────────────────────
            elif mk == "totals":
                for o in ocs:
                    name  = str(o.get("name", "")).strip().lower()
                    price = float(o.get("price", 0) or 0)
                    # line may be on the outcome or on the market
                    line  = float(o.get("point") or pts or 0)
                    if not price or not line:
                        continue
                    if name == "over":
                        if   line == 1.5: od.over_15_odds  = price
                        elif line == 2.5: od.over_25_odds  = price
                        elif line == 3.5: od.over_35_odds  = price
                        elif line == 4.5: od.over_45_odds  = price
                    elif name == "under":
                        if   line == 1.5: od.under_15_odds = price
                        elif line == 2.5: od.under_25_odds = price
                        elif line == 3.5: od.under_35_odds = price
                        elif line == 4.5: od.under_45_odds = price

            # ── Asian Handicap  (all lines) ────────────────────────
            elif mk == "spreads":
                for o in ocs:
                    name  = str(o.get("name", "")).strip()
                    price = float(o.get("price", 0) or 0)
                    line  = float(o.get("point") or pts or 0)
                    if not price or line is None:
                        continue
                    nl = name.lower()
                    if nl in ("home", home_name.lower()):
                        if line not in ah_lines_raw:
                            ah_lines_raw[line] = {}
                        ah_lines_raw[line]["home_odds"] = price
                        ah_lines_raw[line]["line"]      = line
                    elif nl in ("away", away_name.lower()):
                        if line not in ah_lines_raw:
                            ah_lines_raw[line] = {}
                        ah_lines_raw[line]["away_odds"] = price
                        ah_lines_raw[line]["line"]      = line

        # ── Collate AH lines ────────────────────────────────────────
        if ah_lines_raw:
            complete = [
                v for v in ah_lines_raw.values()
                if v.get("home_odds") and v.get("away_odds")
            ]
            complete.sort(key=lambda x: abs(x["line"]))   # closest to 0 first
            od.ah_lines = complete
            if complete:
                # Primary line: the one closest to a balanced market (odds ~2.0)
                def _balance(entry: Dict) -> float:
                    h, a = entry.get("home_odds", 2), entry.get("away_odds", 2)
                    return abs(h - a)
                primary = min(complete, key=_balance)
                od.ah_line      = primary["line"]
                od.ah_home_odds = primary["home_odds"]
                od.ah_away_odds = primary["away_odds"]

        # Require at least 1X2 to be valid
        if od.home_odds <= 1 or od.draw_odds <= 1 or od.away_odds <= 1:
            return None

        # ── Derive Double Chance and DNB ────────────────────────────
        _derive_markets(od)

        return od

    def _extract_best_composite(
        self,
        event: Dict,
        bookmakers: List[Dict],
    ) -> Optional["OddsData"]:
        """
        Build a composite OddsData using the best price for each outcome
        across all bookmakers.  Used when no preferred bookmaker is available.
        """
        home_name = str(event.get("home_team", "")).strip()
        away_name = str(event.get("away_team", "")).strip()
        home_lower = home_name.lower()
        away_lower = away_name.lower()

        # Accumulators: best price per market × outcome
        best: Dict[str, float] = {}

        ah_all: Dict[float, Dict[str, float]] = {}

        for bk in bookmakers:
            for market in bk.get("markets", []):
                mk  = market.get("key", "")
                pts = market.get("point")
                ocs = market.get("outcomes", [])

                if mk == "h2h":
                    for o in ocs:
                        name  = str(o.get("name", "")).strip().lower()
                        price = float(o.get("price", 0) or 0)
                        if price <= 1:
                            continue
                        if name in ("home", home_lower):
                            best["home"] = max(best.get("home", 0), price)
                        elif name == "draw":
                            best["draw"] = max(best.get("draw", 0), price)
                        elif name in ("away", away_lower):
                            best["away"] = max(best.get("away", 0), price)

                elif mk == "totals":
                    for o in ocs:
                        name  = str(o.get("name", "")).strip().lower()
                        price = float(o.get("price", 0) or 0)
                        line  = float(o.get("point") or pts or 0)
                        if not price or not line:
                            continue
                        key = f"{name}_{line}"
                        best[key] = max(best.get(key, 0), price)

                elif mk == "spreads":
                    for o in ocs:
                        name  = str(o.get("name", "")).strip()
                        price = float(o.get("price", 0) or 0)
                        line  = float(o.get("point") or pts or 0)
                        if not price or line is None:
                            continue
                        nl = name.lower()
                        if line not in ah_all:
                            ah_all[line] = {}
                        if nl in ("home", home_lower):
                            ah_all[line]["home_odds"] = max(ah_all[line].get("home_odds", 0), price)
                            ah_all[line]["line"]      = line
                        elif nl in ("away", away_lower):
                            ah_all[line]["away_odds"] = max(ah_all[line].get("away_odds", 0), price)
                            ah_all[line]["line"]      = line

        if not (best.get("home", 0) > 1 and best.get("draw", 0) > 1 and best.get("away", 0) > 1):
            return None

        od = OddsData(
            match_id  = str(event.get("id", "")),
            home_team = home_name,
            away_team = away_name,
            home_odds = best["home"],
            draw_odds = best["draw"],
            away_odds = best["away"],
            bookmaker = "best",
        )

        # Totals
        for line in (1.5, 2.5, 3.5, 4.5):
            ov_key = f"over_{line}"
            un_key = f"under_{line}"
            ov = best.get(ov_key)
            un = best.get(un_key)
            attr_over  = f"over_{str(line).replace('.','')[0:2]}_odds"  # over_15_odds etc
            attr_under = f"under_{str(line).replace('.','')[0:2]}_odds"
            if ov:  setattr(od, attr_over,  ov)
            if un:  setattr(od, attr_under, un)

        # AH
        if ah_all:
            complete = [v for v in ah_all.values() if v.get("home_odds") and v.get("away_odds")]
            complete.sort(key=lambda x: abs(x["line"]))
            od.ah_lines = complete
            if complete:
                primary         = min(complete, key=lambda e: abs(e.get("home_odds", 2) - e.get("away_odds", 2)))
                od.ah_line      = primary["line"]
                od.ah_home_odds = primary["home_odds"]
                od.ah_away_odds = primary["away_odds"]

        _derive_markets(od)
        return od

    async def get_odds_movement(
        self,
        match_id: str,
        sport: str = "soccer_epl",
        hours_back: int = 24,
    ) -> List[Dict]:
        """Track odds movement over time (requires historical data / premium tier)."""
        logger.warning(f"Odds movement tracking not fully implemented for {match_id}")
        return []

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
