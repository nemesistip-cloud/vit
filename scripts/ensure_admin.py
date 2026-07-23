#!/usr/bin/env python3
"""
ensure_admin.py — Idempotent admin user bootstrap.

Creates the admin user if it does not already exist.
If the user already exists, syncs the password so the env-var credential
is always authoritative (re-hashes and persists on every deploy when the
stored hash doesn't match ADMIN_PASSWORD).

Reads ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_USERNAME from env.
Safe to run on every deploy.
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
    from app.auth.jwt_utils import hash_password, verify_password

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL.lower()))
        existing = result.scalar_one_or_none()

        if existing:
            # Sync password: if the stored hash doesn't match the env-var password,
            # update it so the configured credential is always authoritative.
            pw_ok = False
            try:
                pw_ok = verify_password(ADMIN_PASSWORD, existing.hashed_password or "")
            except Exception:
                pw_ok = False

            if not pw_ok:
                existing.hashed_password = hash_password(ADMIN_PASSWORD)
                # Ensure admin role and active state are correct
                existing.role = "admin"
                existing.is_active = True
                await db.commit()
                print(
                    f"[ensure_admin] Admin user '{ADMIN_EMAIL}' password synced "
                    f"from ADMIN_PASSWORD env var (id={existing.id})."
                )
            else:
                print(
                    f"[ensure_admin] Admin user '{ADMIN_EMAIL}' exists and "
                    f"password is current (id={existing.id})."
                )
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
