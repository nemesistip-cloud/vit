# app/tasks/edges.py
import logging

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    from app.services.edge_database import EdgeDatabase
    from app.db.database import AsyncSessionLocal

    @shared_task(name="recalculate_edges_task")
    def recalculate_edges_task(bet_side: str, edge_value: float):
        import asyncio

        async def _recalculate():
            async with AsyncSessionLocal() as db:
                edge_db = EdgeDatabase(db)
                await edge_db.update_edge_performance(
                    edge_id=f"{bet_side}_edge",
                    new_roi=edge_value,
                    new_edge_value=edge_value
                )
                await db.commit()

        asyncio.run(_recalculate())
        logger.info(f"Edges recalculated for {bet_side}")

except ImportError:
    class _FakeTask:
        def delay(self, *args, **kwargs):
            logger.debug("Celery not available — task skipped")

    recalculate_edges_task = _FakeTask()
