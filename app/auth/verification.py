"""Email verification and password reset — DB-backed, multi-worker safe.

SEC-03: Tokens are stored in the email_tokens table as SHA-256 hashes.
In-memory dicts (_verify_tokens, _reset_tokens) are gone — tokens now survive
restarts and work correctly across multiple Uvicorn workers.
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
from app.db.models import User, EmailToken
from app.auth.jwt_utils import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

_TOKEN_TTL_HOURS = 24
_RESET_TTL_HOURS = 2


def _make_token() -> str:
    return secrets.token_urlsafe(32)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _send_email(to: str, subject: str, body: str) -> None:
    """Stub — replace with Resend / SMTP transport when ready."""
    smtp_host = os.getenv("SMTP_HOST", "")
    if smtp_host:
        try:
            import smtplib
            import email.mime.text as _mime
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


async def _store_token(
    db: AsyncSession, user_id: int, purpose: str, token: str, ttl_hours: int
) -> None:
    """Persist a hashed token, removing any previous token for the same user+purpose."""
    await db.execute(
        delete(EmailToken).where(
            EmailToken.user_id == user_id,
            EmailToken.purpose == purpose,
        )
    )
    record = EmailToken(
        token_hash=_hash_token(token),
        user_id=user_id,
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    )
    db.add(record)
    await db.commit()


async def _consume_token(
    db: AsyncSession, token: str, purpose: str
) -> Optional[EmailToken]:
    """Look up a token by hash. Returns the record if valid; marks it used. Returns None if not found or expired."""
    token_hash = _hash_token(token)
    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token_hash == token_hash,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return None
    if datetime.now(timezone.utc) > record.expires_at:
        await db.delete(record)
        await db.commit()
        return None
    record.used_at = datetime.now(timezone.utc)
    await db.commit()
    return record


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
    await _store_token(db, user.id, "verify", token, _TOKEN_TTL_HOURS)

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
    record = await _consume_token(db, body.token, "verify")
    if not record:
        raise HTTPException(400, "Invalid or expired verification token.")

    result = await db.execute(select(User).where(User.id == record.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found.")

    user.is_verified = True
    await db.commit()
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
    await _store_token(db, user.id, "reset", token, _RESET_TTL_HOURS)

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

    record = await _consume_token(db, body.token, "reset")
    if not record:
        raise HTTPException(400, "Invalid or expired reset token.")

    result = await db.execute(select(User).where(User.id == record.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found.")

    user.hashed_password = hash_password(body.new_password)
    await db.commit()

    return {"message": "Password reset successfully. You can now log in with your new password."}
