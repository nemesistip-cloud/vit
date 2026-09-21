"""
TRACK-017: Affiliate Execution Hub
Generates deep-links for sportsbook partners with full UTM attribution,
per-user affiliate IDs, and revenue tracking metadata.

Supported providers: betway, sportybet, bet9ja, 1xbet, msport, betking, nairabet, parimatch
"""
from __future__ import annotations

import urllib.parse
from typing import Dict, List, Optional


class AffiliateService:
    """
    Generates affiliate deep-links for sportsbooks.
    Supports 8 major Nigerian/African bookmakers in production-ready formats.
    """

    # Base URLs — all providers accept query-param slips
    BOOKMAKER_BASE_URLS: Dict[str, str] = {
        "betway":    "https://www.betway.com.ng/multi-selection?",
        "sportybet": "https://www.sportybet.com/ng/m/slip?",
        "bet9ja":    "https://sports.bet9ja.com/selection?",
        "1xbet":     "https://1xbet.ng/en/line/football?",
        "msport":    "https://www.msport.com/ng/sports/prematch?",
        "betking":   "https://www.betking.com/sports/s/coupon?",
        "nairabet":  "https://www.nairabet.com/bet-slip?",
        "parimatch": "https://ng.parimatch.com/en/coupons?",
    }

    # Provider-specific affiliate parameter names
    _AFFILIATE_PARAM: Dict[str, str] = {
        "betway":    "affiliateId",
        "sportybet": "affiliate_id",
        "bet9ja":    "affiliateId",
        "1xbet":     "aff_id",
        "msport":    "affiliate",
        "betking":   "aff",
        "nairabet":  "ref",
        "parimatch": "source",
    }

    # Internal TheOddsAPI market → display name mapping
    PROVIDER_MARKET_MAP: Dict[str, Dict[str, str]] = {
        "theoddsapi": {
            "h2h":     "1x2",
            "totals":  "over_under",
            "spreads": "handicap",
        }
    }

    @staticmethod
    def supported_providers() -> List[str]:
        return sorted(AffiliateService.BOOKMAKER_BASE_URLS.keys())

    @staticmethod
    def generate_deep_link(
        provider: str,
        match_id: str,
        selection_id: str,
        affiliate_id: str = "vit_platform",
        utm_source: str = "vit_app",
        utm_medium: str = "app",
        utm_campaign: str = "prediction_redirect",
        user_ref: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a single-selection affiliate deep-link.

        Args:
            provider:      bookmaker slug (e.g. "betway")
            match_id:      external match ID for this bookmaker
            selection_id:  external selection/outcome ID
            affiliate_id:  VIT platform affiliate code
            utm_source:    UTM source tag
            utm_medium:    UTM medium tag
            utm_campaign:  UTM campaign tag
            user_ref:      optional per-user sub-affiliate reference
        """
        provider = provider.lower()
        base_url = AffiliateService.BOOKMAKER_BASE_URLS.get(provider)
        if not base_url:
            return None

        aff_key = AffiliateService._AFFILIATE_PARAM.get(provider, "affiliateId")
        params: Dict[str, str] = {
            aff_key:         affiliate_id,
            "utm_source":    utm_source,
            "utm_medium":    utm_medium,
            "utm_campaign":  utm_campaign,
        }
        if user_ref:
            params["sub1"] = user_ref

        # Provider-specific selection encoding
        if provider == "sportybet":
            params["selectionIds"] = selection_id
        elif provider == "betway":
            params["ms"] = f"{match_id},{selection_id}"
        elif provider == "bet9ja":
            params["matchId"] = match_id
            params["selectionId"] = selection_id
        elif provider == "1xbet":
            params["match"] = match_id
            params["outcome"] = selection_id
        elif provider == "msport":
            params["eventId"] = match_id
            params["selection"] = selection_id
        elif provider == "betking":
            params["event"] = match_id
            params["market"] = selection_id
        elif provider == "nairabet":
            params["event_id"] = match_id
            params["selection_id"] = selection_id
        elif provider == "parimatch":
            params["event"] = match_id
            params["bet"] = selection_id
        else:
            params["matchId"] = match_id
            params["selectionId"] = selection_id

        return base_url + urllib.parse.urlencode(params)

    @staticmethod
    def generate_multi_selection_link(
        provider: str,
        selections: List[Dict[str, str]],
        affiliate_id: str = "vit_platform",
        utm_source: str = "vit_app",
        utm_medium: str = "app",
        utm_campaign: str = "prediction_redirect",
        user_ref: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a multi-selection accumulator deep-link.

        Each dict in ``selections`` must contain ``match_id`` and ``selection_id``.
        """
        provider = provider.lower()
        base_url = AffiliateService.BOOKMAKER_BASE_URLS.get(provider)
        if not base_url or not selections:
            return None

        aff_key = AffiliateService._AFFILIATE_PARAM.get(provider, "affiliateId")
        params: Dict[str, str] = {
            aff_key:         affiliate_id,
            "utm_source":    utm_source,
            "utm_medium":    utm_medium,
            "utm_campaign":  utm_campaign,
        }
        if user_ref:
            params["sub1"] = user_ref

        if provider == "sportybet":
            params["selectionIds"] = ",".join(s["selection_id"] for s in selections)
        elif provider == "betway":
            params["ms"] = ";".join(f"{s['match_id']},{s['selection_id']}" for s in selections)
        elif provider in ("bet9ja", "nairabet", "parimatch"):
            params["selectionIds"] = ",".join(s["selection_id"] for s in selections)
        elif provider == "1xbet":
            params["events"] = ",".join(s["match_id"] for s in selections)
            params["outcomes"] = ",".join(s["selection_id"] for s in selections)
        elif provider in ("msport", "betking"):
            params["events"] = ",".join(
                f"{s['match_id']}:{s['selection_id']}" for s in selections
            )
        else:
            params["selectionIds"] = ",".join(s["selection_id"] for s in selections)

        return base_url + urllib.parse.urlencode(params)

    @staticmethod
    def get_market_mapping(market_type: str, provider: str) -> str:
        """Return the display name for an internal market type."""
        return (
            AffiliateService.PROVIDER_MARKET_MAP
            .get(provider.lower(), {})
            .get(market_type, market_type)
        )

    @staticmethod
    def build_attribution_metadata(
        provider: str,
        user_id: Optional[int],
        match_id: Optional[int],
        utm_source: str,
        utm_medium: str,
        utm_campaign: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict:
        """
        Return a dict suitable for logging an AffiliateClick record.
        Centralises attribution field population so routes stay thin.
        """
        return {
            "provider_name":  provider.lower(),
            "user_id":        user_id,
            "match_id":       match_id,
            "utm_source":     utm_source,
            "utm_medium":     utm_medium,
            "utm_campaign":   utm_campaign,
            "ip_address":     ip_address,
            "user_agent":     user_agent,
        }
