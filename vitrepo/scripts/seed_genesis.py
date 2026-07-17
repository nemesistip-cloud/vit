#!/usr/bin/env python3
"""
Idempotent genesis-block seeder.

Called from start_production.sh before uvicorn starts.
Creates the genesis block if it doesn't exist yet.
Exits 0 on success or if genesis already present; exits 1 on connection failure
(non-fatal — the start script logs a warning and continues).
"""
import os
import sys
import asyncio

DATABASE_URL = os.getenv("DATABASE_URL", "")
if "postgres" not in DATABASE_URL:
    print("[seed_genesis] Not a Postgres DB — skipping.", flush=True)
    sys.exit(0)

# Make PYTHONPATH include the repo root so all app imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main():
    from app.db.database import AsyncSessionLocal
    from vit_chain.genesis import ensure_genesis

    try:
        async with AsyncSessionLocal() as session:
            block = await session.run_sync(lambda _: None)  # warm connection
    except Exception as e:
        print(f"[seed_genesis] DB connection failed: {e}", flush=True)
        sys.exit(1)

    try:
        async with AsyncSessionLocal() as session:
            from vit_chain.core.chain import VITChain
            chain = VITChain()
            existing = await chain.get_latest_block(session)
            if existing is not None:
                print(
                    f"[seed_genesis] Genesis already present (height={existing.height}, "
                    f"hash={existing.block_hash[:16]}...) — skipping.",
                    flush=True,
                )
                return

        print("[seed_genesis] No blocks found — creating genesis block...", flush=True)
        async with AsyncSessionLocal() as session:
            block = await ensure_genesis(session)
            await session.commit()
            print(
                f"[seed_genesis] Genesis block created: height={block.height}, "
                f"hash={block.block_hash[:16]}...",
                flush=True,
            )
    except Exception as e:
        print(f"[seed_genesis] Failed to create genesis block: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
