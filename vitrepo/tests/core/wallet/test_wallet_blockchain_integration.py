import pytest
from app.core.wallet.manager import WalletManager
from app.core.wallet.models import AccountType

@pytest.mark.asyncio
async def test_address_generation_indexing(db_session):
    manager = WalletManager(db_session)

    account = await manager.create_account("owner_integration")
    wallet = await manager.create_wallet(account.id, name="Integration Wallet")

    # Generate additional address
    address = await manager.generate_address(wallet.id, "base")
    assert address.network == "base"
    assert address.wallet_id == wallet.id

    # Verify indexing
    lookup = await manager.address_repo.get_by_address("base", address.address)
    assert lookup is not None
    assert lookup.wallet_id == wallet.id
