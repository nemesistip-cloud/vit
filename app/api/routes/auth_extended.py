"""
Extended auth routes:
  - Google OAuth (Firebase ID token → VIT JWT)
  - Wallet authentication (SIWE — Sign-In With Ethereum)

These extend the existing /api/auth/* namespace without modifying working routes.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import time
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    hash_password,
)
from app.db.database import get_db
from app.db.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth — Extended"])

# ── SIWE nonce store (in-memory; upgrade to Redis for multi-worker prod) ───────
# { nonce_hex: { "address": str, "issued_at": float } }
_NONCE_STORE: Dict[str, Dict] = {}
_NONCE_TTL = 300  # 5 minutes


def _prune_nonces() -> None:
    now = time.time()
    stale = [k for k, v in _NONCE_STORE.items() if now - v["issued_at"] > _NONCE_TTL]
    for k in stale:
        del _NONCE_STORE[k]


# ═══════════════════════════════════════════════════════════════════════════════
# Google OAuth (Firebase ID token flow)
# ═══════════════════════════════════════════════════════════════════════════════

class GoogleAuthRequest(BaseModel):
    id_token: str                      # Firebase ID token from frontend
    device_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: int
    username: str
    role: str
    is_new_user: bool


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    body: GoogleAuthRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a Firebase Google ID token for a VIT JWT.

    Frontend flow:
      1. User clicks "Sign in with Google" → Firebase Auth popup
      2. Frontend gets firebase.auth().currentUser.getIdToken()
      3. Sends token here → receives VIT access + refresh tokens
    """
    # Verify Firebase token
    try:
        from app.auth.firebase_utils import verify_firebase_id_token
        claims = verify_firebase_id_token(body.id_token)
    except Exception as exc:
        logger.warning("Firebase token verification error: %s", exc)
        claims = None

    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token. Ensure Firebase is configured.",
        )

    email: str = claims.get("email", "")
    name: str = claims.get("name", "") or claims.get("display_name", "")
    if not email:
        raise HTTPException(400, "Google account has no email address")

    # Find or create the VIT user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    is_new = False

    if not user:
        is_new = True
        username = (
            email.split("@")[0].replace(".", "_").lower()[:30]
        )
        # Ensure username uniqueness
        suffix = 1
        base = username
        while True:
            exists = await db.execute(select(User).where(User.username == username))
            if not exists.scalar_one_or_none():
                break
            username = f"{base}{suffix}"
            suffix += 1

        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(secrets.token_hex(32)),  # random, unusable
            role="viewer",
            is_active=True,
        )
        if hasattr(User, "is_verified"):
            user.is_verified = True          # Google verifies emails
        if hasattr(User, "display_name") and name:
            user.display_name = name
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(403, "Account suspended")
    if getattr(user, "is_banned", False):
        raise HTTPException(403, "Account banned")

    access_token  = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Audit
    try:
        from app.db.models import AuditLog
        db.add(AuditLog(
            action="login",
            actor=user.email,
            resource="user",
            resource_id=str(user.id),
            details={"provider": "google", "is_new_user": is_new},
        ))
        await db.commit()
    except Exception:
        await db.rollback()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
        role=user.role,
        is_new_user=is_new,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Wallet Authentication (SIWE — EIP-4361)
# ═══════════════════════════════════════════════════════════════════════════════

class NonceResponse(BaseModel):
    nonce: str
    expires_in: int


class WalletVerifyRequest(BaseModel):
    address: str       # Ethereum address (checksummed or lowercase)
    message: str       # Full SIWE message that was signed
    signature: str     # 0x-prefixed hex signature


@router.get("/wallet/nonce", response_model=NonceResponse)
async def wallet_nonce(request: Request):
    """
    Generate a single-use nonce for SIWE wallet authentication.

    Frontend flow:
      1. GET /api/auth/wallet/nonce → { nonce }
      2. Construct SIWE message including nonce
      3. Sign with ethers.js / wagmi → POST /api/auth/wallet/verify
    """
    _prune_nonces()
    nonce = secrets.token_hex(16)
    _NONCE_STORE[nonce] = {"issued_at": time.time()}
    return NonceResponse(nonce=nonce, expires_in=_NONCE_TTL)


@router.post("/wallet/verify", response_model=TokenResponse)
async def wallet_verify(
    body: WalletVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a SIWE signature and return VIT tokens.

    The message must contain the nonce issued by GET /api/auth/wallet/nonce.
    """
    _prune_nonces()

    # ── Extract nonce from message ─────────────────────────────────────────
    nonce: Optional[str] = None
    for line in body.message.splitlines():
        if line.strip().startswith("Nonce:"):
            nonce = line.split(":", 1)[1].strip()
            break

    if not nonce or nonce not in _NONCE_STORE:
        raise HTTPException(401, "Invalid or expired nonce")

    # Consume nonce (single-use)
    del _NONCE_STORE[nonce]

    # ── Verify EIP-191 signature ───────────────────────────────────────────
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct

        msg = encode_defunct(text=body.message)
        recovered = Account.recover_message(msg, signature=body.signature)
    except Exception as exc:
        logger.warning("SIWE signature recovery failed: %s", exc)
        raise HTTPException(401, "Signature verification failed")

    if recovered.lower() != body.address.lower():
        raise HTTPException(401, "Signature does not match address")

    address = recovered.lower()

    # ── Find or create user ────────────────────────────────────────────────
    result = await db.execute(
        select(User).where(User.wallet_address == address)
    )
    user = result.scalar_one_or_none()
    is_new = False

    if not user:
        is_new = True
        # Check if address column uses 42-char checksum
        checksum_addr = recovered  # keep original case for DB
        username = f"wallet_{address[2:8]}"
        suffix = 1
        base = username
        while True:
            exists = await db.execute(select(User).where(User.username == username))
            if not exists.scalar_one_or_none():
                break
            username = f"{base}{suffix}"
            suffix += 1

        pseudo_email = f"{address}@wallet.vit.network"
        user = User(
            email=pseudo_email,
            username=username,
            hashed_password=hash_password(secrets.token_hex(32)),
            wallet_address=address[:42],   # store checksummed
            role="viewer",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if not user.is_active:
            raise HTTPException(403, "Account suspended")
        if getattr(user, "is_banned", False):
            raise HTTPException(403, "Account banned")

    access_token  = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Audit
    try:
        from app.db.models import AuditLog
        db.add(AuditLog(
            action="login",
            actor=user.email,
            resource="user",
            resource_id=str(user.id),
            details={"provider": "wallet", "address": address, "is_new_user": is_new},
        ))
        await db.commit()
    except Exception:
        await db.rollback()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
        role=user.role,
        is_new_user=is_new,
    )


# ── Link wallet to existing account ───────────────────────────────────────────

class LinkWalletRequest(BaseModel):
    address: str
    message: str
    signature: str


@router.post("/wallet/link")
async def link_wallet(
    body: LinkWalletRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Link a wallet address to an existing authenticated account."""
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct

        msg = encode_defunct(text=body.message)
        recovered = Account.recover_message(msg, signature=body.signature)
    except Exception as exc:
        raise HTTPException(400, f"Signature verification failed: {exc}")

    if recovered.lower() != body.address.lower():
        raise HTTPException(401, "Signature does not match address")

    address = recovered.lower()

    # Check not already taken
    existing = await db.execute(select(User).where(User.wallet_address == address))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Wallet address already linked to another account")

    current_user.wallet_address = address[:42]
    await db.commit()

    return {"status": "linked", "address": address}
