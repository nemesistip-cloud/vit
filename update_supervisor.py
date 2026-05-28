import re

path = 'main.py'
with open(path, 'r') as f:
    content = f.read()

# Add persistent logging logic to the monitor loop
# We need to import BackgroundTaskStatus and datetime

monitor_search = r'async def _monitor\(self\):.*?while not self\.stopping:.*?await asyncio\.sleep\(self\.check_interval\)'
monitor_replace = """async def _monitor(self):
        # ENG-05: Persistent task tracking
        from app.db.database import AsyncSessionLocal
        from app.db.models import BackgroundTaskStatus
        from sqlalchemy import select, update
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        from datetime import datetime, timezone

        while not self.stopping:
            await asyncio.sleep(self.check_interval)"""

content = re.sub(monitor_search, monitor_replace, content, flags=re.DOTALL)

# Add the DB update logic inside the loop
task_loop_search = r'self\._start_task\(name, factory\)'
task_loop_replace = """self._start_task(name, factory)

                # ENG-05: Update DB status
                try:
                    async with AsyncSessionLocal() as db:
                        stmt = sqlite_insert(BackgroundTaskStatus).values(
                            task_name=name,
                            status="running",
                            restart_count=self.restart_counts[name],
                            last_started_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc)
                        ).on_conflict_do_update(
                            index_elements=['task_name'],
                            set_={
                                "status": "running",
                                "restart_count": self.restart_counts[name],
                                "last_started_at": datetime.now(timezone.utc),
                                "updated_at": datetime.now(timezone.utc)
                            }
                        )
                        await db.execute(stmt)
                        await db.commit()
                except Exception as db_err:
                    logger.warning(f"[supervisor] Failed to persist task status to DB: {db_err}")"""

content = content.replace(task_loop_search, task_loop_replace)

# Also handle the crash case
crash_search = r'logger\.error\("\[supervisor\] task failed name=%s error=%s", name, exc, exc_info=exc\)'
crash_replace = """logger.error("[supervisor] task failed name=%s error=%s", name, exc, exc_info=exc)
                        # ENG-05: Log crash to DB
                        try:
                            async with AsyncSessionLocal() as db:
                                await db.execute(
                                    update(BackgroundTaskStatus)
                                    .where(BackgroundTaskStatus.task_name == name)
                                    .values(
                                        status="crashed",
                                        last_crashed_at=datetime.now(timezone.utc),
                                        last_error=str(exc),
                                        updated_at=datetime.now(timezone.utc)
                                    )
                                )
                                await db.commit()
                        except Exception: pass"""

content = content.replace(crash_search, crash_replace)

with open(path, 'w') as f:
    f.write(content)
print("Supervisor updated with ENG-05 persistence")
