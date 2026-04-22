#!/usr/bin/env python
"""Seed platform configuration for wallet module."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import AsyncSessionLocal
from app.modules.wallet.models import PlatformConfig


async def seed_configs():
    """Seed initial platform configuration."""
    
    configs = [
        {
            "key": "vitcoin_price_formula",
            "value": {"method": "revenue_backed", "window_days": 30},
            "description": "VITCoin price calculation formula"
        },
        {
            "key": "vitcoin_price_floor",
            "value": {"amount": 0.001, "currency": "USD"},
            "description": "Minimum VITCoin price"
        },
        {
            "key": "conversion_fee_pct",
            "value": {"value": 1.5},
            "description": "Currency conversion fee percentage"
        },
        {
            "key": "withdrawal_fee_flat",
            "value": {"NGN": 100, "USD": 1, "USDT": 1, "PI": 0.5, "VITCoin": 5},
            "description": "Flat withdrawal fees per currency"
        },
        {
            "key": "auto_withdrawal_limits",
            "value": {"viewer": 0, "analyst": 50, "pro": 200, "validator": 500, "admin": None},
            "description": "Auto-approval limits by role"
        },
        {
            "key": "withdrawal_hold_hours",
            "value": {"value": 24},
            "description": "Hours to hold withdrawals for new addresses"
        },
        {
            "key": "address_age_hours",
            "value": {"value": 48},
            "description": "Minimum address age for withdrawal"
        },
        {
            "key": "exchange_rates",
            "value": {"usd_ngn": 1500, "usd_pi": 0.5},
            "description": "Exchange rates for price display"
        }
    ]
    
    async with AsyncSessionLocal() as db:
        for config in configs:
            # Check if config already exists
            from sqlalchemy import select
            result = await db.execute(
                select(PlatformConfig).where(PlatformConfig.key == config["key"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                platform_config = PlatformConfig(
                    key=config["key"],
                    value=config["value"],
                    description=config["description"]
                )
                db.add(platform_config)
                print(f"✅ Added config: {config['key']}")
            else:
                print(f"⏭️ Config already exists: {config['key']}")
        
        await db.commit()
        print("\n✅ Platform config seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_configs())
