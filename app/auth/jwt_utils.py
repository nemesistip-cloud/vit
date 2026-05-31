# app/auth/jwt_utils.py
# SEC-04: Each token now includes a unique `jti` (JWT ID) claim.
# Call revoke_token(jti, user_id, reason, db) on logout / password-change /
# account suspension to add the jti to the token_blocklist table.
# is_token_revoked(jti, db) is used by the auth middleware.
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from jose import JWTError, jwt

from app.config import JWT_SECRET_KEY as _CONFIG_JWT_SECRET

SECRET_KEY = _CONFIG_JWT_SECRET or os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not configured. Set it in Replit Secrets."
    )
ALGORITHM = "HS256"
def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default

ACCESS_TOKEN_EXPIRE_MINUTES = _int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
REFRESH_TOKEN_EXPIRE_DAYS   = _int_env("REFRESH_TOKEN_EXPIRE_DAYS", 30)


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def revoke_token(
    jti: str,
    user_id: int,
    reason: str,
    db,
    expires_at: Optional[datetime] = None,
) -> None:
    """Add a jti to the blocklist. Call on logout, password-change, or suspension.

    Uses raw SQL to avoid ORM mapper configuration issues — User has many
    lazy relationships that may not be registered yet at call time.
    """
    from sqlalchemy import text

    if expires_at is None:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    existing = await db.execute(
        text("SELECT id FROM token_blocklist WHERE jti = :jti"),
        {"jti": jti},
    )
    if existing.fetchone():
        return

    await db.execute(
        text(
            "INSERT INTO token_blocklist (jti, user_id, reason, expires_at) "
            "VALUES (:jti, :user_id, :reason, :expires_at)"
        ),
        {"jti": jti, "user_id": user_id, "reason": reason, "expires_at": expires_at},
    )
    await db.commit()


async def is_token_revoked(jti: str, db) -> bool:
    """Return True if the jti has been revoked.

    Uses raw SQL to avoid ORM mapper configuration issues — User has many
    lazy relationships (Wallet, UserTaskCompletion, etc.) that trigger full
    mapper reconfiguration and may not all be registered at call time.
    """
    if not jti:
        return False
    from sqlalchemy import text
    result = await db.execute(
        text("SELECT 1 FROM token_blocklist WHERE jti = :jti LIMIT 1"),
        {"jti": jti},
    )
    return result.fetchone() is not None
