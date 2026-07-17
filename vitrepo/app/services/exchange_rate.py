"""
Live exchange rate oracle.

Periodically fetches USD→NGN from Frankfurter (free, no key required) and
updates the PlatformConfig so conversions use current market rates.

Refresh interval: every 30 minutes.
On fetch failure: keeps the last known rate (logs a warning).
"""

import asyncio
import logging
import json
from decimal import Decimal
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

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


async def _update_platform_config(ngn_per_usd: Decimal) -> None:
    """Push the new rate into PlatformConfig 'exchange_rates_usd'."""
    from app.db.database import AsyncSessionLocal
    from app.modules.wallet.models import PlatformConfig

    new_ngn_rate = Decimal("1") / ngn_per_usd

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "exchange_rates_usd"))
        config = result.scalar_one_or_none()
        if config:
            val = dict(config.value)
            val["NGN"] = float(round(new_ngn_rate, 10))
            config.value = val
            await db.commit()
            logger.info(
                "[exchange_rate] Updated PlatformConfig NGN rate: 1 NGN = %.10f USD (1 USD ≈ %.2f NGN)",
                new_ngn_rate, ngn_per_usd,
            )

async def refresh_once() -> None:
    """Fetch rates and update the platform config once."""
    ngn_per_usd = await _fetch_ngn_per_usd()
    if ngn_per_usd:
        await _update_platform_config(ngn_per_usd)
    else:
        logger.warning(
            "[exchange_rate] Rate fetch failed — keeping previous NGN rate."
        )


async def start_rate_refresh_loop() -> None:
    """
    Background task: refresh exchange rates every 30 minutes.
    """
    logger.info("[exchange_rate] Starting exchange rate refresh loop (interval=%ds)", _REFRESH_INTERVAL_SECONDS)
    await refresh_once()
    while True:
        await asyncio.sleep(_REFRESH_INTERVAL_SECONDS)
        await refresh_once()
