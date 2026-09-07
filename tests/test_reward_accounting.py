from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.db.models import User
from app.modules.wallet.models import Wallet, WalletTransaction
from app.modules.wallet.services import WalletService


@pytest.mark.asyncio
async def test_vitcoin_deposit_is_idempotent(db_session):
    user = User(email="reward@example.com", username="reward-user")
    db_session.add(user)
    await db_session.flush()

    service = WalletService(db_session)
    first = await service.deposit_vitcoin(
        user_id=user.id,
        amount=Decimal("2.50000000"),
        description="Verified contribution",
        tx_type="reward",
        metadata={"idempotency_key": "contribution:123"},
    )
    second = await service.deposit_vitcoin(
        user_id=user.id,
        amount=Decimal("2.50000000"),
        description="Retry of verified contribution",
        tx_type="reward",
        metadata={"idempotency_key": "contribution:123"},
    )
    await db_session.commit()

    assert first.id == second.id
    transaction_count = await db_session.scalar(
        select(func.count(WalletTransaction.id)).where(
            WalletTransaction.reference == first.reference
        )
    )
    assert transaction_count == 1

    wallet = await db_session.scalar(select(Wallet).where(Wallet.user_id == user.id))
    assert wallet is not None
    assert wallet.vitcoin_balance == Decimal("12.50000000")
