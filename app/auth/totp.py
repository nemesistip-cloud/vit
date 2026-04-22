"""Two-Factor Authentication (TOTP) using RFC 6238 / Google Authenticator compatible.

Requires: pyotp, qrcode, pillow
"""

import base64
import io
import os
from typing import Optional

import pyotp
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth/2fa", tags=["2fa"])

APP_NAME = "VIT Network"


def _get_qr_data_url(provisioning_uri: str) -> str:
    try:
        import qrcode, qrcode.image.svg
        img = qrcode.make(provisioning_uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""


class Enable2FARequest(BaseModel):
    totp_code: str


class Verify2FARequest(BaseModel):
    totp_code: str


class Disable2FARequest(BaseModel):
    totp_code: str
    password: str


@router.post("/setup")
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new TOTP secret and return QR code data URL."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name=APP_NAME)
    qr = _get_qr_data_url(uri)

    user_extra = getattr(user, "totp_secret_pending", None)
    if not hasattr(user, "totp_secret_pending"):
        from sqlalchemy import text
        try:
            async with db.begin_nested():
                await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret TEXT"))
                await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret_pending TEXT"))
                await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE"))
        except Exception:
            pass

    try:
        user.totp_secret_pending = secret
        await db.commit()
    except Exception:
        await db.rollback()

    return {
        "secret": secret,
        "qr_code": qr,
        "provisioning_uri": uri,
        "instructions": "Scan the QR code with Google Authenticator or Authy, then call /auth/2fa/enable with a code to confirm.",
    }


@router.post("/enable")
async def enable_2fa(
    body: Enable2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm 2FA setup by verifying a TOTP code."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    pending = getattr(user, "totp_secret_pending", None)
    if not pending:
        raise HTTPException(400, "No pending 2FA setup. Call /auth/2fa/setup first.")

    totp = pyotp.TOTP(pending)
    if not totp.verify(body.totp_code, valid_window=1):
        raise HTTPException(400, "Invalid TOTP code. Please try again.")

    user.totp_secret = pending
    user.totp_secret_pending = None
    user.totp_enabled = True
    await db.commit()

    return {"message": "Two-factor authentication enabled successfully."}


@router.post("/verify")
async def verify_2fa(
    body: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a TOTP code for a user with 2FA enabled."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if not getattr(user, "totp_enabled", False):
        raise HTTPException(400, "2FA is not enabled for this account.")

    secret = getattr(user, "totp_secret", None)
    if not secret:
        raise HTTPException(400, "2FA secret not found. Please re-setup 2FA.")

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.totp_code, valid_window=1):
        raise HTTPException(401, "Invalid or expired 2FA code.")

    return {"message": "2FA verified successfully.", "verified": True}


@router.post("/disable")
async def disable_2fa(
    body: Disable2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA after verifying current TOTP code + password."""
    from app.auth.jwt_utils import verify_password

    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Incorrect password.")

    if not getattr(user, "totp_enabled", False):
        raise HTTPException(400, "2FA is not currently enabled.")

    secret = getattr(user, "totp_secret", None)
    if secret:
        totp = pyotp.TOTP(secret)
        if not totp.verify(body.totp_code, valid_window=1):
            raise HTTPException(401, "Invalid TOTP code.")

    user.totp_secret = None
    user.totp_secret_pending = None
    user.totp_enabled = False
    await db.commit()

    return {"message": "Two-factor authentication disabled."}


@router.get("/status")
async def totp_status(current_user: User = Depends(get_current_user)):
    """Get 2FA status for current user."""
    return {
        "totp_enabled": getattr(current_user, "totp_enabled", False),
        "has_pending_setup": bool(getattr(current_user, "totp_secret_pending", None)),
    }
