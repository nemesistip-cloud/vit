import asyncio
import os
import sys
sys.path.append(os.getcwd())

async def sync_schema():
    try:
        from app.db.database import engine, Base
        import app.db.models
        import app.modules.wallet.models
        import app.modules.blockchain.models
        import app.modules.training.models
        import app.modules.ai.models
        import app.data.models
        import app.modules.notifications.models
        import app.modules.marketplace.models
        import app.modules.trust.models
        import app.modules.rewards.models
        import app.modules.bridge.models
        import app.modules.developer.models
        import app.modules.governance.models
        import app.modules.referral.models
        import app.modules.tasks.models
        import app.modules.storage_verification.models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print('[init_db] DB Schema: All tables verified/created.')
        await engine.dispose()
    except Exception as e:
        print(f'[init_db] DB Sync Error: {e}')

if __name__ == "__main__":
    asyncio.run(sync_schema())
