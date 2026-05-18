"""
Encrypted secrets manager — Value Intelligence Trust (VIT).

Keys can come from two sources (checked in order):
  1. Replit Secrets / env vars already in os.environ at startup
  2. PlatformSecret DB table (encrypted with Fernet derived from JWT_SECRET_KEY)

On startup load_db_secrets_to_env() is called. It reads every row from the DB
and loads the decrypted value into os.environ — only for keys not already set
by Replit Secrets. This means admin-panel changes survive server restarts.

Priority:  Replit Secret > DB secret > unset
"""
import base64
import hashlib
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        raw = os.getenv("JWT_SECRET_KEY", "vit-default-secret-change-in-production")
        key_bytes = hashlib.sha256(raw.encode()).digest()
        _fernet = Fernet(base64.urlsafe_b64encode(key_bytes))
    return _fernet


def encrypt_secret(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()


async def load_db_secrets_to_env() -> int:
    """
    Called once at startup. Loads all DB-stored secrets into os.environ.
    Skips keys that are already set by Replit Secrets (env takes priority).
    Returns number of secrets injected.
    """
    try:
        from app.db.database import AsyncSessionLocal
        from app.modules.wallet.models import PlatformSecret
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            rows = (await session.execute(select(PlatformSecret))).scalars().all()
            loaded = 0
            for row in rows:
                if not os.environ.get(row.key):
                    try:
                        os.environ[row.key] = decrypt_secret(row.encrypted_value)
                        loaded += 1
                    except Exception as exc:
                        logger.warning("Could not decrypt DB secret %s: %s", row.key, exc)
            if loaded:
                logger.info("✅ Loaded %d DB-stored secret(s) into environment", loaded)
            return loaded
    except Exception as exc:
        logger.warning("Could not load DB secrets at startup: %s", exc)
        return 0


async def save_secret_to_db(key: str, value: str, updated_by: Optional[int] = None) -> None:
    """Encrypt and upsert a secret in the PlatformSecret table."""
    from app.db.database import AsyncSessionLocal
    from app.modules.wallet.models import PlatformSecret
    from sqlalchemy import select

    encrypted = encrypt_secret(value)
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(PlatformSecret).where(PlatformSecret.key == key)
        )).scalar_one_or_none()
        if row:
            row.encrypted_value = encrypted
            row.updated_by = updated_by
        else:
            session.add(PlatformSecret(key=key, encrypted_value=encrypted, updated_by=updated_by))
        await session.commit()


async def delete_secret_from_db(key: str) -> bool:
    """Remove a key from the DB. Returns True if it existed."""
    from app.db.database import AsyncSessionLocal
    from app.modules.wallet.models import PlatformSecret
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(PlatformSecret).where(PlatformSecret.key == key)
        )).scalar_one_or_none()
        if not row:
            return False
        await session.delete(row)
        await session.commit()
        return True


async def get_db_secret_keys() -> set:
    """Return the set of key names currently stored in the DB."""
    try:
        from app.db.database import AsyncSessionLocal
        from app.modules.wallet.models import PlatformSecret
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            rows = (await session.execute(select(PlatformSecret.key))).scalars().all()
            return set(rows)
    except Exception:
        return set()
