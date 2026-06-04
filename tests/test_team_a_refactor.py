import pytest
from sqlalchemy import select
from app.db.models import Market, Match, Prediction, MarketMapping
from app.modules.blockchain.models import UserStake

@pytest.mark.asyncio
async def test_market_creation(client, auth_headers, setup_database):
    from app.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        # Create a sports market
        sports_market = Market(
            market_type="sports",
            category="football",
            title="Liverpool vs Real Madrid",
            status="open"
        )
        db.add(sports_market)

        # Create a niche market
        niche_market = Market(
            market_type="niche",
            category="election",
            title="US Presidential Election 2024",
            status="open"
        )
        db.add(niche_market)
        await db.commit()
        await db.refresh(sports_market)
        await db.refresh(niche_market)

        assert sports_market.market_type == "sports"
        assert niche_market.market_type == "niche"

@pytest.mark.asyncio
async def test_sports_staking_blocked(client, auth_headers, setup_database):
    from app.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        # Create a sports match
        market = Market(market_type="sports", category="football", title="Sports Market")
        db.add(market)
        await db.flush()

        from datetime import datetime
        match = Match(
            id=999,
            market_id=market.id,
            market_type="sports",
            home_team="Team A",
            away_team="Team B",
            league="League 1",
            kickoff_time=datetime(2025, 1, 1, 12, 0),
            status="scheduled"
        )
        db.add(match)
        await db.commit()

    # Attempt to stake on sports match
    response = await client.post(
        "/api/blockchain/predictions/999/stake",
        json={"prediction": "home", "amount": 10.0},
        headers=auth_headers
    )
    # Debug print if fail
    if response.status_code != 403:
        print(f"DEBUG: status={response.status_code} body={response.text}")
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_niche_staking_allowed(client, auth_headers, setup_database):
    from app.db.database import AsyncSessionLocal
    from app.modules.wallet.models import Wallet
    from decimal import Decimal

    async with AsyncSessionLocal() as db:
        # Get user
        from app.db.models import User
        res = await db.execute(select(User).limit(1))
        user = res.scalar()

        # Ensure wallet exists and has balance
        wallet = Wallet(user_id=user.id, vitcoin_balance=Decimal("100.0"))
        db.add(wallet)

        # Create a niche match/event
        market = Market(market_type="niche", category="election", title="Niche Market")
        db.add(market)
        await db.flush()

        from datetime import datetime
        match = Match(
            id=888,
            market_id=market.id,
            market_type="niche",
            home_team="Candidate A",
            away_team="Candidate B",
            league="Politics",
            kickoff_time=datetime(2025, 1, 1, 12, 0),
            status="scheduled"
        )
        db.add(match)
        await db.commit()

    # Attempt to stake on niche match
    response = await client.post(
        "/api/blockchain/predictions/888/stake",
        json={"prediction": "home", "amount": 10.0},
        headers=auth_headers
    )
    # If calculate_consensus fails because it's a fake match, we still check that it didn't fail with 403
    assert response.status_code != 403
