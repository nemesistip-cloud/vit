import pytest
from datetime import datetime, timezone, timedelta
from app.data.match_dedup import compute_fingerprint, normalize_team_name
from app.api.routes.sports import _match_teams, _norm_team
from app.api.routes.matches import _compute_match_data_status
from app.db.models import Match
from app.modules.wallet.models import Wallet

def test_team_normalization_and_matching():
    # Football-Data vs The Odds API name variants
    h1, a1 = "Tottenham Hotspur FC", "Fulham FC"
    h2, a2 = "Tottenham Hotspur", "Fulham"

    assert _match_teams(h1, a1, h2, a2) is True
    assert normalize_team_name(h1) == normalize_team_name(h2)

def test_fingerprint_deduplication():
    kickoff = datetime(2026, 12, 2, 20, 0, 0)
    fp1 = compute_fingerprint("Tottenham Hotspur FC", "Fulham FC", kickoff, "Premier League")
    fp2 = compute_fingerprint("Tottenham Hotspur", "Fulham", kickoff, "premier_league")

    assert fp1 == fp2
    assert fp1 != ""

def test_freshness_classification_policy():
    now = datetime.now(timezone.utc)

    # 1. Fresh match (<15 mins old) -> LIVE
    m_live = Match(
        source="footballdata",
        updated_at=now - timedelta(minutes=5),
        created_at=now - timedelta(minutes=5)
    )
    assert _compute_match_data_status(m_live, now) == "LIVE"

    # 2. Stale match (>15 mins old) -> DELAYED
    m_delayed = Match(
        source="footballdata",
        updated_at=now - timedelta(minutes=30),
        created_at=now - timedelta(minutes=30)
    )
    assert _compute_match_data_status(m_delayed, now) == "DELAYED"

    # 3. Demo match -> DEMO
    m_demo = Match(
        source="seed_demo",
        updated_at=now - timedelta(minutes=2)
    )
    assert _compute_match_data_status(m_demo, now) == "DEMO"

    # 4. Unverified/unknown match -> UNAVAILABLE
    m_unavail = Match(
        source="unverified",
        updated_at=now
    )
    assert _compute_match_data_status(m_unavail, now) == "UNAVAILABLE"

@pytest.mark.asyncio
async def test_wave0_wallet_isolation_invariant(db_session):
    # Verify wallet model structure and confirm sports operations do not alter balances
    wallet = Wallet(user_id=999, usdt_balance=100.0, vitcoin_balance=50.0)
    db_session.add(wallet)
    await db_session.commit()

    initial_usdt = wallet.usdt_balance
    initial_vitcoin = wallet.vitcoin_balance

    # Match fixture creation does not touch wallet
    match = Match(
        home_team="Arsenal FC",
        away_team="Chelsea FC",
        league="Premier League",
        sport="football",
        kickoff_time=datetime.now(timezone.utc).replace(tzinfo=None),
        opening_odds_home=2.10,
        opening_odds_draw=3.40,
        opening_odds_away=3.20,
    )
    db_session.add(match)
    await db_session.commit()

    assert wallet.usdt_balance == initial_usdt
    assert wallet.vitcoin_balance == initial_vitcoin
