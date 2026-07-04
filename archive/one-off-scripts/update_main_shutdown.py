import os

filepath = 'main.py'
with open(filepath, 'r') as f:
    content = f.read()

# Fix the cleanup logic in the finally block of _run_bootstrap
old_cleanup = """            finally:
                await supervisor.stop()
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                from app.db.database import engine
                await engine.dispose()"""

new_cleanup = """            finally:
                logger.info("[bootstrap] Shutting down background tasks...")
                await supervisor.stop()
                maintenance_tasks = getattr(app.state, "maintenance_tasks", [])
                for task in maintenance_tasks:
                    if not task.done():
                        task.cancel()
                if maintenance_tasks:
                    await asyncio.gather(*maintenance_tasks, return_exceptions=True)

                from app.db.database import engine
                await engine.dispose()
                logger.info("[bootstrap] Database engine disposed")"""

if old_cleanup in content:
    content = content.replace(old_cleanup, new_cleanup)

with open(filepath, 'w') as f:
    f.write(content)
