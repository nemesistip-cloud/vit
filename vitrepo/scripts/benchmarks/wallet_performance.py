import asyncio
import time
import logging
from decimal import Decimal
from app.db.database import AsyncSessionLocal, Base, engine
from app.core.wallet.manager import WalletManager
from app.core.wallet.sdk import WalletSDK
from app.core.wallet.subsystem import WalletSubsystem
from app.core.redis import require_redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")

async def run_benchmarks():
    logger.info("Initializing benchmark environment...")
    from app.core.wallet.models import Base as WalletBase
    async with engine.begin() as conn:
        await conn.run_sync(WalletBase.metadata.create_all)

    class MockApp:
        state = type('State', (), {'redis': None})
    await require_redis(MockApp())

    subsystem = type('MockSubsystem', (), {'get_sdk': lambda: None})
    sdk = WalletSDK(subsystem)

    logger.info("Benchmarking Wallet Creation...")
    start = time.time()
    iters = 10
    for i in range(iters):
        await sdk.create_wallet(f"user_bench_{i}", name=f"Wallet {i}")
    duration = (time.time() - start) / iters * 1000
    logger.info(f"Avg Wallet Creation: {duration:.2f}ms (Target: <100ms)")

    wallets = await sdk.list_wallets("user_bench_0")
    wallet_id = wallets[0]["id"]

    logger.info("Benchmarking Address Generation...")
    async with AsyncSessionLocal() as session:
        manager = WalletManager(session)
        start = time.time()
        for i in range(iters):
            await manager.generate_address(wallet_id, f"net_{i}")
        duration = (time.time() - start) / iters * 1000
        logger.info(f"Avg Address Generation: {duration:.2f}ms (Target: <50ms)")
        await session.commit()

    logger.info("Benchmarking Balance Lookup (Cached)...")
    await sdk.get_balance(wallet_id, "VIT")
    start = time.time()
    iters_lookup = 100
    for i in range(iters_lookup):
        await sdk.get_balance(wallet_id, "VIT")
    duration = (time.time() - start) / iters_lookup * 1000
    logger.info(f"Avg Balance Lookup: {duration:.2f}ms (Target: <5ms)")

    logger.info("Benchmarking Wallet Lookup...")
    start = time.time()
    for i in range(iters_lookup):
        await sdk.list_wallets("user_bench_0")
    duration = (time.time() - start) / iters_lookup * 1000
    logger.info(f"Avg Wallet Lookup: {duration:.2f}ms (Target: <10ms)")

if __name__ == "__main__":
    asyncio.run(run_benchmarks())
