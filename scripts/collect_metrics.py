#!/usr/bin/env python3
"""scripts/collect_metrics.py — compute rolling-window metrics and persist to ModelMetadata

Usage:
    python3 scripts/collect_metrics.py --window 50
"""
import argparse
import asyncio
from pathlib import Path


async def _collect(window: int = 50):
    from app.db.database import AsyncSessionLocal
    from app.services.accuracy_enhancer import rolling_window_accuracy
    from sqlalchemy import select
    from app.modules.ai.models import ModelMetadata

    async with AsyncSessionLocal() as session:
        metrics = await rolling_window_accuracy(session, window=window)
        if not metrics:
            print("No rolling metrics computed — no settled predictions yet.")
            return 0
        updated = 0
        for m in metrics:
            row = (await session.execute(select(ModelMetadata).where(ModelMetadata.key == m.model_key))).scalar_one_or_none()
            if not row:
                continue
            row.accuracy_1x2 = m.accuracy_1x2
            row.log_loss = m.log_loss
            row.brier_score = m.brier
            row.predictions_total = (row.predictions_total or 0) + m.samples
            await session.commit()
            updated += 1
        print(f"Updated {updated} model metadata rows with rolling metrics")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Collect and persist rolling-window model metrics")
    parser.add_argument("--window", type=int, default=50)
    args = parser.parse_args()
    return asyncio.run(_collect(window=args.window))


if __name__ == "__main__":
    raise SystemExit(main())
