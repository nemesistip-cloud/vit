# app/services/exchange_rate.py
"""
Live exchange rate oracle.

Periodically fetches USD→NGN from Frankfurter (free, no key required) and
updates the WalletService in-memory rate table so conversions use current
market rates rather than hardcoded fallbacks.

Refresh interval: every 30 minutes.
On fetch failure: keeps the last known rate (logs a warning).
"""

import asyncio
import logging
from decimal import Decimal

import httpx

logger = logging.getLogger(__name__)

_REFRESH_INTERVAL_SECONDS = 1800  # 30 minutes
_RATE_URL = "https://open.er-api.com/v6/latest/USD"
_TIMEOUT = 10  # seconds
_MAX_RETRIES = 3


async def _fetch_ngn_per_usd() -> Decimal | None:
    """Return how many NGN equal 1 USD, or None if the fetch fails."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_RATE_URL)
                resp.raise_for_status()
                data = resp.json()
                ngn_per_usd = data["rates"]["NGN"]
                return Decimal(str(ngn_per_usd))
        except Exception as exc:
            logger.warning(
                "[exchange_rate] Attempt %d/%d failed: %s",
                attempt, _MAX_RETRIES, exc,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)
    return None


async def _update_wallet_service(ngn_per_usd: Decimal) -> None:
    """Push the new rate into WalletService's in-memory table."""
    from app.modules.wallet.services import WalletService
    new_rate = Decimal("1") / ngn_per_usd
    WalletService._RATES_TO_USD["NGN"] = new_rate
    logger.info(
        "[exchange_rate] Updated NGN rate: 1 NGN = %.8f USD  (1 USD ≈ %.2f NGN)",
        new_rate, ngn_per_usd,
    )


async def refresh_once() -> None:
    """Fetch rates and update the wallet service once."""
    ngn_per_usd = await _fetch_ngn_per_usd()
    if ngn_per_usd:
        await _update_wallet_service(ngn_per_usd)
    else:
        logger.warning(
            "[exchange_rate] Rate fetch failed — keeping previous NGN rate."
        )


async def start_rate_refresh_loop() -> None:
    """
    Background task: refresh exchange rates every 30 minutes.
    Designed to be launched via asyncio.create_task() inside the app lifespan.
    """
    logger.info("[exchange_rate] Starting exchange rate refresh loop (interval=%ds)", _REFRESH_INTERVAL_SECONDS)
    await refresh_once()
    while True:
        await asyncio.sleep(_REFRESH_INTERVAL_SECONDS)
        await refresh_once()
