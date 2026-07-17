#!/usr/bin/env python3
"""
ensure_admin.py — Idempotent admin user bootstrap.

Creates the admin user if it does not already exist.
Reads ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_USERNAME from env.
Safe to run on every deploy; no-ops when the user already exists.
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL",    "admin@vit.network")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")

if not ADMIN_PASSWORD:
    print("[ensure_admin] ADMIN_PASSWORD not set — skipping admin bootstrap.")
    sys.exit(0)


async def main():
    from sqlalchemy import select
    from app.db.database import AsyncSessionLocal
    from app.db.models import User
    from app.auth.jwt_utils import hash_password

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL.lower()))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"[ensure_admin] Admin user '{ADMIN_EMAIL}' already exists (id={existing.id}).")
            return

        admin = User(
            email=ADMIN_EMAIL.lower(),
            username=ADMIN_USERNAME,
            hashed_password=hash_password(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        print(f"[ensure_admin] Admin user '{ADMIN_EMAIL}' created (id={admin.id}).")


if __name__ == "__main__":
    asyncio.run(main())
