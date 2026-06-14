import urllib.parse
from typing import List, Dict, Optional

class AffiliateService:
    """
    Generates affiliate deep-links for sportsbooks.
    Supports Betway, SportyBet, and Bet9ja with production-ready formats.
    """

    BOOKMAKER_BASE_URLS = {
        "betway": "https://www.betway.com.ng/multi-selection?",
        "sportybet": "https://www.sportybet.com/ng/m/slip?",
        "bet9ja": "https://sports.bet9ja.com/selection?"
    }

    # Internal market name mapping
    PROVIDER_MARKET_MAP = {
        "theoddsapi": {
            "h2h": "1x2",
            "totals": "over_under",
            "spreads": "handicap"
        }
    }

    @staticmethod
    def generate_deep_link(
        provider: str,
        match_id: str,
        selection_id: str,
        affiliate_id: str = "vit_platform",
        utm_source: str = "vit_app"
    ) -> Optional[str]:
        """
        Generates a deep-link for a single selection on a sportsbook.
        """
        provider = provider.lower()
        base_url = AffiliateService.BOOKMAKER_BASE_URLS.get(provider)
        if not base_url:
            return None

        params = {
            "affiliateId": affiliate_id,
            "utm_source": utm_source,
            "utm_medium": "app",
            "utm_campaign": "prediction_redirect"
        }

        if provider == "sportybet":
            params.update({"selectionIds": selection_id})
        elif provider == "betway":
            params.update({"ms": f"{match_id},{selection_id}"})
        elif provider == "bet9ja":
            params.update({"matchId": match_id, "selectionId": selection_id})
        else:
            params.update({"matchId": match_id, "selectionId": selection_id})

        return base_url + urllib.parse.urlencode(params)

    @staticmethod
    def generate_multi_selection_link(
        provider: str,
        selections: List[Dict[str, str]],
        affiliate_id: str = "vit_platform",
        utm_source: str = "vit_app"
    ) -> Optional[str]:
        """
        Generates a deep-link for multiple selections (accumulator slip).
        Each selection dict should contain 'match_id' and 'selection_id'.
        """
        provider = provider.lower()
        base_url = AffiliateService.BOOKMAKER_BASE_URLS.get(provider)
        if not base_url:
            return None

        params = {
            "affiliateId": affiliate_id,
            "utm_source": utm_source,
            "utm_medium": "app",
            "utm_campaign": "prediction_redirect"
        }

        if provider == "sportybet":
            sel_ids = ",".join([s["selection_id"] for s in selections])
            params["selectionIds"] = sel_ids
        elif provider == "betway":
            # Format: match1,selection1;match2,selection2
            ms_val = ";".join([f"{s['match_id']},{s['selection_id']}" for s in selections])
            params["ms"] = ms_val
        elif provider == "bet9ja":
            # Bet9ja often uses a comma-separated list of selection IDs
            sel_ids = ",".join([s["selection_id"] for s in selections])
            params["selectionIds"] = sel_ids
        else:
            # Fallback
            sel_ids = ",".join([s["selection_id"] for s in selections])
            params["selectionIds"] = sel_ids

        return base_url + urllib.parse.urlencode(params)

    @staticmethod
    def get_market_mapping(market_type: str, provider: str) -> str:
        """Returns the provider-specific market string."""
        return AffiliateService.PROVIDER_MARKET_MAP.get(provider.lower(), {}).get(market_type, market_type)
