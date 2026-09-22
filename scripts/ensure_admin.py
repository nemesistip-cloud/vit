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

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=False)

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL",    "admin@vit.network")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")

if not ADMIN_PASSWORD:
    print("[ensure_admin] ADMIN_PASSWORD not set — skipping admin bootstrap.")
    sys.exit(0)


def resolve_admin_user(existing_users, admin_email: str, admin_username: str):
    """Prefer the configured admin identity, but keep user id 1 authoritative."""
    if not existing_users:
        return None

    admin_email = (admin_email or "").lower()
    admin_username = (admin_username or "").lower()

    for candidate in existing_users:
        email = getattr(candidate, "email", None)
        if email and email.lower() == admin_email:
            return candidate

    if admin_username:
        for candidate in existing_users:
            username = getattr(candidate, "username", None)
            if username and username.lower() == admin_username:
                return candidate

    for candidate in existing_users:
        if getattr(candidate, "id", None) == 1:
            return candidate

    return existing_users[0]


async def main():
    from sqlalchemy import select
    from app.db.database import AsyncSessionLocal
    from app.db.models import User
    from app.auth.jwt_utils import hash_password, verify_password

    async with AsyncSessionLocal() as db:
        # Resolve by email first, then username, and finally the canonical user id 1.
        # This keeps the first bootstrap account authoritative when the configured
        # admin email rotates or the deployment is recovered from a stale state.
        result = await db.execute(
            select(User).where(User.email == ADMIN_EMAIL.lower())
        )
        email_match = result.scalar_one_or_none()

        username_match = None
        if ADMIN_USERNAME:
            result = await db.execute(
                select(User).where(User.username == ADMIN_USERNAME)
            )
            username_match = result.scalar_one_or_none()

        legacy_admin = None
        result = await db.execute(select(User).where(User.id == 1))
        legacy_admin = result.scalar_one_or_none()

        existing = resolve_admin_user(
            [user for user in (email_match, username_match, legacy_admin) if user is not None],
            ADMIN_EMAIL,
            ADMIN_USERNAME,
        )

        if existing:
            # Keep the configured email/username pair authoritative when the
            # admin email is rotated through Render environment variables, while
            # still enforcing the canonical id=1 super-admin contract.
            identity_changed = (
                existing.id == 1 and (existing.email != ADMIN_EMAIL.lower() or existing.username != ADMIN_USERNAME)
                or existing.email != ADMIN_EMAIL.lower()
                or existing.username != ADMIN_USERNAME
                or existing.role != "super_admin"
                or existing.admin_role != "super_admin"
                or not existing.is_active
            )
            existing.email = ADMIN_EMAIL.lower()
            existing.username = ADMIN_USERNAME
            existing.role = "super_admin"
            existing.admin_role = "super_admin"
            existing.is_active = True

            # Sync password: if the stored hash doesn't match the env-var password,
            # update it so the configured credential is always authoritative.
            pw_ok = False
            try:
                pw_ok = verify_password(ADMIN_PASSWORD, existing.hashed_password or "")
            except Exception:
                pw_ok = False

            if not pw_ok:
                existing.hashed_password = hash_password(ADMIN_PASSWORD)
            if not pw_ok or identity_changed:
                await db.commit()
            if not pw_ok:
                print(
                    f"[ensure_admin] Admin user '{ADMIN_EMAIL}' password synced "
                    f"from ADMIN_PASSWORD env var (id={existing.id})."
                )
            else:
                print(
                    f"[ensure_admin] Admin user '{ADMIN_EMAIL}' exists and "
                    f"password is current (id={existing.id})."
                    + (" Identity fields synchronized." if identity_changed else "")
                )
            return

        admin = User(
            email=ADMIN_EMAIL.lower(),
            username=ADMIN_USERNAME,
            hashed_password=hash_password(ADMIN_PASSWORD),
            role="super_admin",
            admin_role="super_admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        print(f"[ensure_admin] Admin user '{ADMIN_EMAIL}' created (id={admin.id}).")


if __name__ == "__main__":
    asyncio.run(main())
