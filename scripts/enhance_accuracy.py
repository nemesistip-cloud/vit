"""CLI: fit temperature scaling + print rolling-window accuracy report.

Usage:
    python -m scripts.enhance_accuracy              # fit + report
    python -m scripts.enhance_accuracy --report     # report only
    python -m scripts.enhance_accuracy --fit        # fit only
    python -m scripts.enhance_accuracy --window 100
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.db.database import async_session
from app.services.accuracy_enhancer import (
    fit_temperature_from_history,
    rolling_window_accuracy,
)


async def _run(do_fit: bool, do_report: bool, window: int, min_samples: int) -> int:
    out: dict = {}
    async with async_session() as db:
        if do_fit:
            out["temperature_fit"] = await fit_temperature_from_history(
                db, min_samples=min_samples
            )
        if do_report:
            metrics = await rolling_window_accuracy(db, window=window)
            out["rolling_window"] = {
                "window": window,
                "models": [m.__dict__ for m in metrics],
            }
    print(json.dumps(out, indent=2, default=str))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Enhance ensemble accuracy.")
    ap.add_argument("--fit", action="store_true", help="Fit temperature only")
    ap.add_argument("--report", action="store_true", help="Print rolling window report only")
    ap.add_argument("--window", type=int, default=50)
    ap.add_argument("--min-samples", type=int, default=100)
    args = ap.parse_args()

    do_fit = args.fit or not (args.fit or args.report)
    do_report = args.report or not (args.fit or args.report)
    return asyncio.run(_run(do_fit, do_report, args.window, args.min_samples))


if __name__ == "__main__":
    sys.exit(main())
