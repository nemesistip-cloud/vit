#!/usr/bin/env python3
"""Fit Platt + Isotonic calibrators from settled prediction history.

Usage:
    python -m scripts.fit_calibrators [--method both|platt|isotonic] [--min-samples 50]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=["both", "platt", "isotonic"], default="both")
    parser.add_argument("--min-samples", type=int, default=50)
    args = parser.parse_args()

    from app.db.database import AsyncSessionLocal
    # Register all SQLAlchemy mappers exactly like main.py does
    import app.db.models  # noqa: F401
    import app.modules.wallet.models  # noqa: F401
    import app.modules.blockchain.models  # noqa: F401
    import app.modules.training.models  # noqa: F401
    import app.modules.ai.models  # noqa: F401
    import app.data.models  # noqa: F401
    import app.modules.notifications.models  # noqa: F401
    import app.modules.marketplace.models  # noqa: F401
    import app.modules.trust.models  # noqa: F401
    import app.modules.bridge.models  # noqa: F401
    import app.modules.developer.models  # noqa: F401
    import app.modules.governance.models  # noqa: F401
    import app.modules.referral.models  # noqa: F401
    from app.services.calibration import fit_from_history

    async with AsyncSessionLocal() as db:
        report = await fit_from_history(
            db, method=args.method, min_samples=args.min_samples,
        )
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
