"""Email verification and password reset — token-based, no SMTP required.

Tokens are stored in the DB.  In development the token is returned in the API
response so the frontend can display a verification link.  Wire up an SMTP /
SendGrid / Mailgun transport by replacing _send_email() when ready.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.auth.jwt_utils import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

_TOKEN_TTL_HOURS = 24
_RESET_TTL_HOURS = 2

# ---------------------------------------------------------------------------
# In-memory token store (replace with DB-backed table for production scale)
# ---------------------------------------------------------------------------
_verify_tokens: dict[str, dict] = {}
_reset_tokens: dict[str, dict] = {}


def _make_token() -> str:
    return secrets.token_urlsafe(32)


async def _send_email(to: str, subject: str, body: str) -> None:
    """Stub — replace with real SMTP / SendGrid / Mailgun transport."""
    smtp_host = os.getenv("SMTP_HOST", "")
    if smtp_host:
        try:
            import smtplib, email.mime.text as _mime
            msg = _mime.MIMEText(body, "html")
            msg["Subject"] = subject
            msg["From"] = os.getenv("SMTP_FROM", "noreply@vit.network")
            msg["To"] = to
            with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587"))) as s:
                if os.getenv("SMTP_USER"):
                    s.starttls()
                    s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
                s.send_message(msg)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f"Email send failed: {exc}")
    else:
        import logging
        logging.getLogger(__name__).info(f"[email stub] TO={to} SUBJECT={subject}")


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

class SendVerificationRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    token: str


@router.post("/send-verification")
async def send_verification(body: SendVerificationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        return {"message": "If that email exists, a verification link has been sent."}

    if user.is_verified:
        return {"message": "Email already verified.", "already_verified": True}

    token = _make_token()
    _verify_tokens[token] = {
        "user_id": user.id,
        "email": user.email,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS),
    }

    base_url = os.getenv("FRONTEND_URL", "")
    link = f"{base_url}/verify-email?token={token}"
    await _send_email(
        user.email,
        "Verify your VIT Network email",
        f"<p>Click the link to verify your email:</p><p><a href='{link}'>{link}</a></p>"
        f"<p>This link expires in {_TOKEN_TTL_HOURS} hours.</p>",
    )

    response: dict = {"message": "Verification email sent (check spam if not received)."}
    if not os.getenv("SMTP_HOST"):
        response["dev_token"] = token
        response["dev_link"] = link
    return response


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    record = _verify_tokens.get(body.token)
    if not record:
        raise HTTPException(400, "Invalid or expired verification token.")

    if datetime.now(timezone.utc) > record["expires_at"]:
        del _verify_tokens[body.token]
        raise HTTPException(400, "Verification token has expired. Please request a new one.")

    result = await db.execute(select(User).where(User.id == record["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found.")

    user.is_verified = True
    await db.commit()
    del _verify_tokens[body.token]

    return {"message": "Email verified successfully!", "email": user.email}


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    if not user:
        return {"message": "If that email exists, a reset link has been sent."}

    token = _make_token()
    _reset_tokens[token] = {
        "user_id": user.id,
        "email": user.email,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=_RESET_TTL_HOURS),
    }

    base_url = os.getenv("FRONTEND_URL", "")
    link = f"{base_url}/reset-password?token={token}"
    await _send_email(
        user.email,
        "Reset your VIT Network password",
        f"<p>Click the link to reset your password:</p><p><a href='{link}'>{link}</a></p>"
        f"<p>This link expires in {_RESET_TTL_HOURS} hours. If you did not request this, ignore this email.</p>",
    )

    response: dict = {"message": "Password reset link sent (check spam if not received)."}
    if not os.getenv("SMTP_HOST"):
        response["dev_token"] = token
        response["dev_link"] = link
    return response


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    if len(body.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    record = _reset_tokens.get(body.token)
    if not record:
        raise HTTPException(400, "Invalid or expired reset token.")

    if datetime.now(timezone.utc) > record["expires_at"]:
        del _reset_tokens[body.token]
        raise HTTPException(400, "Reset token has expired. Please request a new reset link.")

    result = await db.execute(select(User).where(User.id == record["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found.")

    user.hashed_password = hash_password(body.new_password)
    await db.commit()
    del _reset_tokens[body.token]

    return {"message": "Password reset successfully. You can now log in with your new password."}
