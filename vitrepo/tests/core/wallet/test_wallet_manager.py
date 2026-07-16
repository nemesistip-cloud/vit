import pytest
from app.core.wallet.manager import WalletManager
from app.core.wallet.models import AccountType, WalletStatus

@pytest.mark.asyncio
async def test_wallet_lifecycle(db_session):
    manager = WalletManager(db_session)

    # Create Account
    account = await manager.create_account("owner_lifecycle", name="Institutional Account", account_type=AccountType.INSTITUTIONAL)
    assert account.owner_id == "owner_lifecycle"

    # Create Wallet
    wallet = await manager.create_wallet(account.id, name="Trading Wallet")
    assert wallet.account_id == account.id
    assert wallet.status == WalletStatus.ACTIVE

    # Get Summary
    summary = await manager.get_wallet_summary(wallet.id)
    assert summary["name"] == "Trading Wallet"
    assert "vit" in summary["addresses"]
