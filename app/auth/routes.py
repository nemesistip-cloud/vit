# app/auth/routes.py
import uuid
import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.db.database import get_db
from app.db.models import User, AuditLog
from app.modules.wallet.models import Wallet
from app.auth.telegram import validate_telegram_init_data
from app.auth.jwt_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
)
from app.modules.platform.integration import platform_integration
from app.core.event_bus import event_bus

# ---------------------------------------------------------------------------
# Brute-force / account-lockout state
# In-memory with Redis promotion on next iteration. Protects /auth/login.
# ---------------------------------------------------------------------------
_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_LOGIN_LOCK = Lock()
_MAX_ATTEMPTS   = 10          # per key per window
_WINDOW_SECONDS = 900         # 15-minute sliding window
_LOCKOUT_SECONDS = 1800       # 30-minute hard lockout after max exceeded


def _get_login_key(request: Request, email: str) -> str:
    """Derive a per-(IP, email) bucket key."""
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    return f"{ip}:{email.lower()}"


def _check_and_record_attempt(key: str, success: bool) -> None:
    """
    Raise 429 if the key is in lockout or has exceeded the attempt limit.
    Record a new attempt timestamp on failure; clear on success.
    """
    now = time.monotonic()
    with _LOGIN_LOCK:
        attempts = _LOGIN_ATTEMPTS[key]
        # Evict timestamps outside the window
        cutoff = now - _WINDOW_SECONDS
        attempts[:] = [t for t in attempts if t > cutoff]

        if success:
            _LOGIN_ATTEMPTS.pop(key, None)
            return

        if attempts and (now - attempts[0]) < _LOCKOUT_SECONDS and len(attempts) >= _MAX_ATTEMPTS:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Too many failed login attempts. "
                    f"Account temporarily locked. Try again later."
                ),
            )
        attempts.append(now)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)

def is_transient_db_error(exception):
    msg = str(exception).lower()
    return any(x in msg for x in ["connection was closed", "not connected", "pool", "broken pipe", "protocol error", "timeout", "reset by peer", "io error", "unexpected eof", "connection reset"])

async def _write_audit(db: AsyncSession, action: str, email: str, target_type: str, target_id: str):
    try:
        audit = AuditLog(
            action=action,
            actor=email,
            resource=target_type,
            resource_id=target_id,
            details={"email": email},
        )
        db.add(audit)
        await db.commit()
    except Exception:
        await db.rollback()

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("password")
    def password_strength(cls, v):
        import re
        if len(v) < 10:
            raise ValueError("Password must be at least 10 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", v):
            raise ValueError("Password must contain at least one special character")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    created_at: datetime

class TwoFARequired(BaseModel):
    two_fa_required: bool = True
    pre_auth_token: str

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    stmt = select(User).where(or_(User.email == body.email.lower(), User.username == body.username))
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email or username already exists")

    hashed = hash_password(body.password)
    user = User(
        email=body.email.lower(),
        username=body.username,
        hashed_password=hashed,
        role="user",
    )
    db.add(user)
    await db.flush()

    user_id = user.id
    user_email = user.email
    user_username = user.username
    user_role = user.role

    # Create default wallet
    wallet = Wallet(user_id=user_id, vitcoin_balance=Decimal("0"))
    db.add(wallet)

    await db.commit()

    access_token = create_access_token({"sub": str(user_id), "role": user_role})
    refresh_token = create_refresh_token({"sub": str(user_id)})

    await _write_audit(db, "user.register", user_email, "auth", str(user_id))

    await event_bus.publish(
        "user.registered",
        {"user_id": str(user_id), "email": user_email},
        sender="auth.routes",
    )
    await platform_integration.index_entity(
        "users",
        str(user_id),
        user_username,
        f"{user_username} {user_email}",
        {"role": user_role},
    )
    await platform_integration.publish_notification(
        str(user_id),
        "Welcome to VIT",
        "Your account is ready. Start exploring the platform.",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user_id,
        username=user_username,
        role=user_role,
    )

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    login_key = _get_login_key(request, body.email)

    # Check lockout BEFORE touching the DB (fail fast, no timing oracle)
    _check_and_record_attempt(login_key, success=False)

    stmt = select(User).where(User.email == body.email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        # Attempt already recorded above
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is deactivated")

    # Successful auth — clear lockout state
    _check_and_record_attempt(login_key, success=True)

    now = datetime.now(timezone.utc)
    user.last_login = now
    await db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    await _write_audit(db, "user.login", user.email, "auth", str(user.id))

    await event_bus.publish(
        "user.logged_in",
        {"user_id": str(user.id), "email": user.email},
        sender="auth.routes",
    )
    await platform_integration.index_entity(
        "users",
        str(user.id),
        user.username,
        f"{user.username} {user.email}",
        {"role": user.role},
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )

@router.get("/me", response_model=UserResponse)
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: AsyncSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload.get("sub"))
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Phase 3: Revoke the old refresh token's JTI (refresh token rotation)
    old_jti = payload.get("jti")
    if old_jti:
        from datetime import timedelta
        try:
            await revoke_token(old_jti, int(payload.get("sub", 0)), "refresh_rotation", db)
        except Exception:
            pass  # blocklist failure is non-fatal for rotation

    user_id = int(payload.get("sub"))
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


class LogoutRequest(BaseModel):
    refresh_token: str = ""  # Optional — include to revoke refresh token too


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    body: LogoutRequest = LogoutRequest(),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current access token (and optionally the refresh token).

    Returns 204 No Content on success. Idempotent — revoking an already-revoked
    token is not an error.
    """
    # Revoke access token
    if credentials and credentials.credentials:
        payload = decode_token(credentials.credentials)
        if payload:
            jti = payload.get("jti")
            user_id = int(payload.get("sub", 0))
            if jti and user_id:
                try:
                    await revoke_token(jti, user_id, "logout", db)
                except Exception:
                    pass

    # Optionally revoke refresh token
    if body.refresh_token:
        rpayload = decode_token(body.refresh_token)
        if rpayload:
            rjti = rpayload.get("jti")
            ruid = int(rpayload.get("sub", 0))
            if rjti and ruid:
                try:
                    await revoke_token(rjti, ruid, "logout", db)
                except Exception:
                    pass
