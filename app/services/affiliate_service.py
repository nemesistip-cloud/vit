import urllib.parse
from typing import Dict, Optional

class AffiliateService:
    """
    Generates affiliate deep-links for sportsbooks.
    Supports Betway, SportyBet, and Bet9ja.
    """

    BOOKMAKER_BASE_URLS = {
        "betway": "https://betway.com.ng/multi-selection?",
        "sportybet": "https://www.sportybet.com/ng/m/slip?",
        "bet9ja": "https://sports.bet9ja.com/selection?"
    }

    # Example mapping for providers to internal market names
    PROVIDER_MARKET_MAP = {
        "theoddsapi": {
            "h2h": "1x2",
            "totals": "over_under"
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
        Generates a deep-link for a specific selection on a sportsbook.
        """
        base_url = AffiliateService.BOOKMAKER_BASE_URLS.get(provider.lower())
        if not base_url:
            return None

        params = {
            "matchId": match_id,
            "selectionId": selection_id,
            "affiliateId": affiliate_id,
            "utm_source": utm_source,
            "utm_medium": "app",
            "utm_campaign": "prediction_redirect"
        }

        return base_url + urllib.parse.urlencode(params)

    @staticmethod
    def get_market_mapping(market_type: str, provider: str) -> str:
        """Returns the provider-specific market string."""
        return AffiliateService.PROVIDER_MARKET_MAP.get(provider.lower(), {}).get(market_type, market_type)
