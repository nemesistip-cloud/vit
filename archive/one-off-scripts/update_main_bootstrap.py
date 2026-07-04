import os

filepath = 'main.py'
with open(filepath, 'r') as f:
    content = f.read()

# Refactor historical_backfill_task to have a longer delay and less aggressive initial run
old_backfill = """            async def historical_backfill_task():
                \"\"\"Run historical backfill + prediction seeder once after server starts (non-blocking).\"\"\"
                await asyncio.sleep(60)  # give the server time to fully start first"""

new_backfill = """            async def historical_backfill_task():
                \"\"\"Run historical backfill + prediction seeder once after server starts (non-blocking).\"\"\"
                # In production, we delay this significantly to ensure the API stays responsive
                # and doesn't hit RAM limits during simultaneous model loading.
                is_prod = get_env("ENVIRONMENT") == "production"
                delay = 300 if is_prod else 60
                logger.info(f"[bootstrap] historical_backfill_task will start in {delay}s")
                await asyncio.sleep(delay)"""

if old_backfill in content:
    content = content.replace(old_backfill, new_backfill)

# Move tasks registration to a background function to avoid blocking port open
old_tasks_registration = """            tasks = [
                asyncio.create_task(auto_settle_loop(), name="auto-settle"),
                asyncio.create_task(live_match_tracker_loop(), name="live-match-tracker"),
                asyncio.create_task(model_accountability_loop(), name="model-accountability"),
                asyncio.create_task(vitcoin_pricing_loop(), name="vitcoin-pricing"),
                asyncio.create_task(tachyon_worker_loop(), name="tachyon-verification"),
                asyncio.create_task(subscription_expiry_loop(), name="subscription-expiry"),
                asyncio.create_task(start_rate_refresh_loop(), name="exchange-rate-oracle"),
                asyncio.create_task(sync_upcoming_loop(), name="fixture-sync"),
                asyncio.create_task(historical_backfill_task(), name="historical-backfill"),
                asyncio.create_task(bridge_relayer_loop(), name="bridge-relayer"),
            ]"""

new_tasks_registration = """            async def _start_maintenance_tasks():
                \"\"\"Start all non-supervised background loops with staggered delays.\"\"\"
                is_prod = get_env("ENVIRONMENT") == "production"
                if is_prod:
                    await asyncio.sleep(10) # staggering start

                app.state.maintenance_tasks = [
                    asyncio.create_task(auto_settle_loop(), name="auto-settle"),
                    asyncio.create_task(live_match_tracker_loop(), name="live-match-tracker"),
                    asyncio.create_task(model_accountability_loop(), name="model-accountability"),
                    asyncio.create_task(vitcoin_pricing_loop(), name="vitcoin-pricing"),
                    asyncio.create_task(tachyon_worker_loop(), name="tachyon-verification"),
                    asyncio.create_task(subscription_expiry_loop(), name="subscription-expiry"),
                    asyncio.create_task(start_rate_refresh_loop(), name="exchange-rate-oracle"),
                    asyncio.create_task(sync_upcoming_loop(), name="fixture-sync"),
                    asyncio.create_task(historical_backfill_task(), name="historical-backfill"),
                    asyncio.create_task(bridge_relayer_loop(), name="bridge-relayer"),
                ]
                logger.info(f"✅ Started {len(app.state.maintenance_tasks)} background maintenance tasks")

            asyncio.create_task(_start_maintenance_tasks())"""

if old_tasks_registration in content:
    content = content.replace(old_tasks_registration, new_tasks_registration)

with open(filepath, 'w') as f:
    f.write(content)
