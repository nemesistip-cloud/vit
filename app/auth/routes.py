# app/auth/routes.py
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User, AuditLog
from app.modules.wallet.models import Wallet
from app.auth.jwt_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


# ── Schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    referral_code: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        import re
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            errors.append("at least one number")
        if not re.search(r"[^A-Za-z0-9]", v):
            errors.append("at least one special character")
        if errors:
            raise ValueError("Password must contain " + ", ".join(errors))
        return v

    @field_validator("username")
    @classmethod
    def username_clean(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


class TwoFARequired(BaseModel):
    """Returned when the user has 2FA enabled — full tokens are withheld."""
    requires_2fa: bool = True
    pre_auth_token: str
    token_type: str = "pre_auth"


class Complete2FARequest(BaseModel):
    pre_auth_token: str
    totp_code: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Helpers ───────────────────────────────────────────────────────────

def _is_first_user() -> bool:
    """If no admin exists yet, the first registered user becomes admin."""
    return False  # Checked per-request below


async def _write_audit(db: AsyncSession, action: str, actor: str, resource: str = None, resource_id: str = None):
    try:
        db.add(AuditLog(
            action=action,
            actor=actor,
            resource=resource,
            resource_id=resource_id,
            status="success",
        ))
        await db.commit()
    except Exception:
        await db.rollback()


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing_email = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    existing_username = await db.execute(select(User).where(User.username == body.username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")

    # First user ever becomes admin — use count() not select(User) to avoid loading all rows
    from sqlalchemy import func as _func
    is_first = ((await db.execute(select(_func.count(User.id)))).scalar() or 0) == 0

    user = User(
        email=body.email.lower(),
        username=body.username,
        hashed_password=hash_password(body.password),
        role="admin" if is_first else "user",
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()  # assigns user.id without committing

    # Auto-create wallet with 100 VITCoin onboarding bonus
    wallet = Wallet(
        id=str(uuid.uuid4()),
        user_id=user.id,
        vitcoin_balance=Decimal("100.00000000"),
    )
    db.add(wallet)

    if body.referral_code:
        from app.modules.referral.routes import apply_referral_bonus
        try:
            await apply_referral_bonus(db, user, body.referral_code, commit=False)
        except HTTPException:
            await db.rollback()
            raise
        except Exception as exc:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Referral could not be applied: {exc}")

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post("/login")
async def login(body: LoginRequest, request: Request = None, db: AsyncSession = Depends(get_db)):
    from app.core.rate_limit import check_login_allowed, record_login_failure, clear_login_failures

    client_ip = request.client.host if request and request.client else None

    try:
        check_login_allowed(body.email, client_ip)
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))

    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        record_login_failure(body.email, client_ip)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    clear_login_failures(body.email)

    # ── 2FA gate: if enabled, return a short-lived pre-auth token ───────
    if getattr(user, "totp_enabled", False):
        from datetime import timedelta as _td
        pre_auth = create_access_token(
            {"sub": str(user.id), "role": user.role, "type": "pre_auth"},
            expires_delta=_td(minutes=5),
        )
        return TwoFARequired(pre_auth_token=pre_auth)

    # ── Full login ───────────────────────────────────────────────────────
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    await _write_audit(db, "user.login", user.email, "auth", str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post("/2fa/complete-login", response_model=TokenResponse)
async def complete_login_2fa(body: Complete2FARequest, db: AsyncSession = Depends(get_db)):
    """Exchange a pre-auth token + TOTP code for full access/refresh tokens."""
    import pyotp

    payload = decode_token(body.pre_auth_token)
    if not payload or payload.get("type") != "pre_auth":
        raise HTTPException(status_code=401, detail="Invalid or expired 2FA session. Please log in again.")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    secret = getattr(user, "totp_secret", None)
    if not secret:
        raise HTTPException(status_code=400, detail="2FA secret missing. Please re-setup 2FA.")

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.totp_code.strip(), valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid or expired 2FA code.")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    await _write_audit(db, "user.login.2fa", user.email, "auth", str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.get("/me")
async def me(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.core.roles import get_permissions_for_admin_role
    admin_role = getattr(user, "admin_role", None)
    raw_tier = getattr(user, "subscription_tier", "viewer") or "viewer"
    # v4.6.1: Admins (including super_admin) always get effective elite tier
    # so feature gates don't lock them out of their own platform.
    effective_tier = "elite" if admin_role else raw_tier
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "admin_role": admin_role,
        "subscription_tier": effective_tier,
        "raw_subscription_tier": raw_tier,
        "is_banned": getattr(user, "is_banned", False),
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "last_login": user.last_login,
        "permissions": get_permissions_for_admin_role(admin_role) if admin_role else [],
    }
