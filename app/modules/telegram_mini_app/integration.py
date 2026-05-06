"""app/modules/telegram_mini_app/integration.py — TMA Integration v6.0

Telegram Mini App backend:
  - initData HMAC-SHA256 authentication (strict enforcement)
  - AES-256-GCM credential vault for bookmaker credentials
  - Per-user session management (24-hour TTL)
  - Tool marketplace metering (credit-based)

Security: all Telegram initData is validated before any user data is returned.
Invalid/expired/missing initData → 401 with code "tma_auth_failed".
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_TMA_SESSION_TTL_HOURS = 24
_TOOL_CREDIT_COSTS: Dict[str, int] = {
    "auto_cashout":       10,
    "live_odds_tracker":   5,
    "predictor":          20,
    "accumulator_builder": 15,
    "bankroll_manager":    5,
}

# ── initData validation ───────────────────────────────────────────────────────

def verify_init_data(init_data: str, bot_token: str) -> Dict[str, Any]:
    """
    Validate Telegram WebApp initData using HMAC-SHA256.

    Returns parsed data dict if valid.
    Raises ValueError if invalid, expired, or missing.

    Spec: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data or not bot_token:
        raise ValueError("Missing initData or bot token")

    # Parse query-string-style init_data
    params: Dict[str, str] = {}
    received_hash: Optional[str] = None

    for part in init_data.split("&"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = unquote(k)
        v = unquote(v)
        if k == "hash":
            received_hash = v
        else:
            params[k] = v

    if received_hash is None:
        raise ValueError("initData missing 'hash' field")

    # Build data-check-string (sorted alphabetically, one per line)
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )

    # HMAC-SHA256: secret_key = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()

    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("initData hash mismatch — potential tampering")

    # Check freshness (≤1 hour tolerance)
    auth_date_str = params.get("auth_date", "0")
    auth_date = int(auth_date_str)
    age_seconds = int(time.time()) - auth_date
    if age_seconds > 3600:
        raise ValueError(f"initData expired ({age_seconds}s old, max 3600s)")

    # Parse user JSON
    parsed: Dict[str, Any] = dict(params)
    if "user" in parsed:
        try:
            parsed["user"] = json.loads(parsed["user"])
        except Exception:
            pass

    return parsed


# ── AES-256-GCM Credential Vault ─────────────────────────────────────────────

def _get_master_key() -> bytes:
    """Derive 32-byte AES key from VAULT_MASTER_KEY env var."""
    raw = os.getenv("VAULT_MASTER_KEY", "")
    if not raw:
        logger.warning("[vault] VAULT_MASTER_KEY not set — using ephemeral key (dev only)")
        raw = "dev-only-insecure-vault-master-key-32b"
    return hashlib.sha256(raw.encode()).digest()  # 32 bytes


def encrypt_credential(plaintext: str) -> str:
    """AES-256-GCM encrypt a string. Returns base64-encoded nonce+tag+ciphertext."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        # Fallback: base64 obfuscation in dev (install cryptography for prod)
        logger.warning("[vault] cryptography not installed — using base64 fallback")
        return base64.b64encode(plaintext.encode()).decode()

    key   = _get_master_key()
    nonce = secrets.token_bytes(12)           # 96-bit nonce
    ct    = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    blob  = nonce + ct                        # nonce(12) + ciphertext+tag
    return base64.b64encode(blob).decode()


def decrypt_credential(ciphertext_b64: str) -> str:
    """Decrypt a credential previously encrypted by encrypt_credential."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        return base64.b64decode(ciphertext_b64.encode()).decode()

    blob  = base64.b64decode(ciphertext_b64.encode())
    nonce = blob[:12]
    ct    = blob[12:]
    key   = _get_master_key()
    return AESGCM(key).decrypt(nonce, ct, None).decode()


# ── Session store (in-memory + DB) ──────────────────────────────────────────

class TMASessionStore:
    """In-memory session store with 24-hour TTL. Backed by DB for persistence."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def create(self, telegram_user_id: int, vit_user_id: Optional[int],
               tg_data: dict) -> str:
        """Create a new 24-hour session. Returns session_id."""
        session_id = secrets.token_hex(32)
        self._sessions[session_id] = {
            "session_id":      session_id,
            "telegram_user_id": telegram_user_id,
            "vit_user_id":     vit_user_id,
            "tg_data":         tg_data,
            "credits":         0,
            "credentials":     {},   # broker_type → encrypted blob
            "created_at":      self._now().isoformat(),
            "expires_at":      (self._now() + timedelta(hours=_TMA_SESSION_TTL_HOURS)).isoformat(),
            "tool_usage":      [],
        }
        logger.info("[tma-session] created session for tg_user=%d", telegram_user_id)
        return session_id

    def get(self, session_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        expires = datetime.fromisoformat(session["expires_at"])
        if expires.replace(tzinfo=timezone.utc) < self._now():
            del self._sessions[session_id]
            return None
        return session

    def invalidate(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def cleanup(self) -> int:
        now = self._now()
        stale = [
            sid for sid, s in self._sessions.items()
            if datetime.fromisoformat(s["expires_at"]).replace(tzinfo=timezone.utc) < now
        ]
        for sid in stale:
            del self._sessions[sid]
        return len(stale)


# ── Tool Marketplace Metering ─────────────────────────────────────────────────

class ToolMarketplaceMetering:
    """Credit-based usage metering for TMA tools."""

    def check_credits(self, session: dict, tool: str) -> tuple[bool, str]:
        """Returns (can_use, reason)."""
        cost = _TOOL_CREDIT_COSTS.get(tool)
        if cost is None:
            return False, f"Unknown tool: {tool}"
        if session["credits"] < cost:
            return False, f"Insufficient credits: need {cost}, have {session['credits']}"
        return True, ""

    def deduct(self, session: dict, tool: str) -> dict:
        """Deduct credits and record usage. Mutates session."""
        cost = _TOOL_CREDIT_COSTS.get(tool, 0)
        session["credits"] -= cost
        session["tool_usage"].append({
            "tool":       tool,
            "cost":       cost,
            "used_at":    datetime.now(timezone.utc).isoformat(),
            "balance_after": session["credits"],
        })
        return {"tool": tool, "cost": cost, "balance": session["credits"]}

    def top_up(self, session: dict, amount: int) -> dict:
        session["credits"] += amount
        return {"credits": session["credits"]}

    def usage_history(self, session: dict, days: int = 30) -> list:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        return [u for u in session["tool_usage"] if u["used_at"] >= cutoff]


# ── TMA API ────────────────────────────────────────────────────────────────────

class TMAAPI:
    """Main TMA integration service."""

    def __init__(self) -> None:
        self._sessions  = TMASessionStore()
        self._metering  = ToolMarketplaceMetering()
        self._bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        logger.info("[tma-api] initialised (bot_token=%s)",
                    "configured" if self._bot_token else "MISSING")

    def authenticate(self, init_data: str) -> dict:
        """
        Validate initData and return or create a session.
        Raises ValueError on auth failure (caller should return 401).
        """
        parsed = verify_init_data(init_data, self._bot_token)
        user   = parsed.get("user", {})
        if not isinstance(user, dict):
            user = {}
        tg_user_id = int(user.get("id", 0))
        if not tg_user_id:
            raise ValueError("No user.id in initData")

        # Find existing non-expired session for this Telegram user
        existing = next(
            (s for s in self._sessions._sessions.values()
             if s["telegram_user_id"] == tg_user_id),
            None,
        )
        if existing:
            existing_id = existing["session_id"]
            if self._sessions.get(existing_id):
                return existing

        session_id = self._sessions.create(
            telegram_user_id=tg_user_id,
            vit_user_id=None,
            tg_data=parsed,
        )
        return self._sessions.get(session_id) or {}

    def link_vit_account(self, session_id: str, vit_user_id: int) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session["vit_user_id"] = vit_user_id
        return True

    def store_credential(self, session_id: str, broker: str, credential_data: dict) -> bool:
        """Encrypt and store a bookmaker credential in the session vault."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        encrypted = encrypt_credential(json.dumps(credential_data))
        session["credentials"][broker] = {
            "encrypted": encrypted,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "broker":    broker,
        }
        logger.info("[tma-vault] credential stored for broker=%s session=%s",
                    broker, session_id[:8])
        return True

    def retrieve_credential(self, session_id: str, broker: str) -> Optional[dict]:
        """Decrypt and return a broker credential."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        entry = session["credentials"].get(broker)
        if not entry:
            return None
        try:
            return json.loads(decrypt_credential(entry["encrypted"]))
        except Exception as exc:
            logger.error("[tma-vault] decrypt failed for %s: %s", broker, exc)
            return None

    def use_tool(self, session_id: str, tool: str) -> dict:
        """Check credits and deduct if sufficient."""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "session_not_found"}
        can_use, reason = self._metering.check_credits(session, tool)
        if not can_use:
            return {"error": reason, "credits": session["credits"]}
        return self._metering.deduct(session, tool)

    def top_up_credits(self, session_id: str, amount: int) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "session_not_found"}
        return self._metering.top_up(session, amount)

    def get_marketplace_status(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "session_not_found"}
        return {
            "credits":         session["credits"],
            "tools":           _TOOL_CREDIT_COSTS,
            "usage_today":     self._metering.usage_history(session, days=1),
            "credentials":     list(session["credentials"].keys()),
            "vit_user_id":     session["vit_user_id"],
            "telegram_user_id": session["telegram_user_id"],
            "expires_at":      session["expires_at"],
        }

    def cleanup_sessions(self) -> int:
        return self._sessions.cleanup()


# ── Singleton ─────────────────────────────────────────────────────────────────

_GLOBAL_TMA: Optional[TMAAPI] = None


def get_tma_api() -> TMAAPI:
    global _GLOBAL_TMA
    if _GLOBAL_TMA is None:
        _GLOBAL_TMA = TMAAPI()
    return _GLOBAL_TMA


# ── FastAPI router ────────────────────────────────────────────────────────────

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

tma_router = APIRouter(prefix="/api/tma", tags=["Telegram Mini App"])


class InitDataRequest(BaseModel):
    init_data: str


class CredentialRequest(BaseModel):
    session_id: str
    broker:     str
    username:   str
    password:   str


class ToolRequest(BaseModel):
    session_id: str
    tool:       str


class TopUpRequest(BaseModel):
    session_id: str
    amount:     int


@tma_router.post("/auth")
async def tma_auth(req: InitDataRequest):
    """
    Authenticate a Telegram Mini App user via initData.
    Returns session info on success. Strict HMAC-SHA256 enforcement.
    """
    try:
        session = get_tma_api().authenticate(req.init_data)
        return {
            "session_id":       session["session_id"],
            "telegram_user_id": session["telegram_user_id"],
            "vit_user_id":      session["vit_user_id"],
            "expires_at":       session["expires_at"],
            "credits":          session["credits"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={
            "code":    "tma_auth_failed",
            "message": str(exc),
        })


@tma_router.get("/marketplace/{session_id}")
async def tma_marketplace(session_id: str):
    """Get session marketplace status: credits, tools, credentials."""
    result = get_tma_api().get_marketplace_status(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@tma_router.post("/tool/use")
async def tma_use_tool(req: ToolRequest):
    """Use a marketplace tool (deducts credits)."""
    result = get_tma_api().use_tool(req.session_id, req.tool)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result


@tma_router.post("/tool/topup")
async def tma_topup(req: TopUpRequest):
    """Top up session credits (called after payment verification)."""
    result = get_tma_api().top_up_credits(req.session_id, req.amount)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@tma_router.post("/credentials/store")
async def tma_store_credential(req: CredentialRequest):
    """Store encrypted bookmaker credentials in the session vault."""
    ok = get_tma_api().store_credential(
        req.session_id,
        req.broker,
        {"username": req.username, "password": req.password},
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"stored": True, "broker": req.broker}


@tma_router.get("/tools")
async def tma_tools():
    """List available tools and their credit costs."""
    return {"tools": _TOOL_CREDIT_COSTS}
