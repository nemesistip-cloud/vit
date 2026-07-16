import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.wallet.engine import BalanceEngine
from app.core.wallet.models import CoreAsset, CoreWallet, CoreAccount, AccountType

@pytest.mark.asyncio
async def test_balance_update_atomic(db_session: AsyncSession):
    # Setup
    asset = CoreAsset(symbol="TEST_ATOMIC", name="Test Asset", precision=18)
    account = CoreAccount(owner_id="owner_atomic", account_type=AccountType.INDIVIDUAL)
    db_session.add_all([asset, account])
    await db_session.commit()

    wallet = CoreWallet(account_id=account.id, name="Test Wallet")
    db_session.add(wallet)
    await db_session.commit()

    engine = BalanceEngine(db_session)

    # Initial Update
    await engine.update_balance(wallet.id, "TEST_ATOMIC", Decimal("100.50"), balance_type="confirmed")
    await db_session.commit()

    # Verify
    bal = await engine.balance_repo.get_wallet_balance(wallet.id, "TEST_ATOMIC")
    assert bal.confirmed_balance == Decimal("100.50")

    # Partial Spend (Reserved)
    await engine.update_balance(wallet.id, "TEST_ATOMIC", Decimal("50.00"), balance_type="reserved")
    await db_session.commit()

    # Verify spendable
    spendable = await engine.get_spendable_balance(wallet.id, "TEST_ATOMIC")
    assert spendable == Decimal("50.50")

    # Over-reserve should fail
    with pytest.raises(ValueError, match="Insufficient spendable balance"):
        await engine.update_balance(wallet.id, "TEST_ATOMIC", Decimal("60.00"), balance_type="reserved")
