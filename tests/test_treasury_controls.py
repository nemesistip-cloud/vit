import pytest
from decimal import Decimal

from app.modules.treasury.service import allocate_from_pool, deposit_to_pool
from app.modules.treasury.routes import list_grants


@pytest.mark.asyncio
async def test_treasury_rejects_non_positive_deposit():
    with pytest.raises(ValueError, match="greater than zero"):
        await deposit_to_pool(None, None, Decimal("0"), "test")


@pytest.mark.asyncio
async def test_treasury_rejects_non_positive_allocation():
    with pytest.raises(ValueError, match="greater than zero"):
        await allocate_from_pool(None, None, Decimal("-1"), "test")


@pytest.mark.asyncio
async def test_list_grants_uses_treasury_grant_model():
    class Result:
        def scalars(self):
            return self

        def all(self):
            return []

    class Database:
        async def execute(self, _query):
            return Result()

    assert await list_grants(Database()) == {"proposals": []}