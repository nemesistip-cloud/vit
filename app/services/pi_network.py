"""app/services/pi_network.py — Pi Network Server-Side API integration.

Pi Network Platform API (https://api.minepi.com):
  GET  /v2/payments/{payment_id}           → fetch payment details
  POST /v2/payments/{payment_id}/approve   → server-side approve
  POST /v2/payments/{payment_id}/complete  → complete with on-chain txid
  GET  /v2/me                              → fetch Pi user info (access_token required)

Authentication: Server-to-Server calls use Basic auth with PI_APP_ID:PI_APP_SECRET
or Bearer token (access_token for user-facing calls).

Pi Network Sandbox: sandbox.minepi.com — set PI_SANDBOX_MODE=true for development.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_MAINNET_BASE = "https://api.minepi.com"
_SANDBOX_BASE = "https://api.minepi.com"  # Pi uses same base; sandbox controlled via API key prefix


def _get_config() -> dict:
    from app.config import PI_APP_ID, PI_APP_SECRET, PI_SANDBOX_MODE, PI_WEBHOOK_SECRET
    return {
        "app_id": PI_APP_ID or os.getenv("PI_APP_ID", ""),
        "app_secret": PI_APP_SECRET or os.getenv("PI_APP_SECRET", ""),
        "sandbox": (PI_SANDBOX_MODE or os.getenv("PI_SANDBOX_MODE", "false")).lower() in ("1", "true", "yes"),
        "webhook_secret": PI_WEBHOOK_SECRET or os.getenv("PI_WEBHOOK_SECRET", ""),
    }


def _api_base() -> str:
    cfg = _get_config()
    return _SANDBOX_BASE if cfg["sandbox"] else _MAINNET_BASE


def _headers(access_token: Optional[str] = None) -> dict:
    cfg = _get_config()
    if access_token:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    app_secret = cfg["app_secret"]
    if not app_secret:
        return {"Content-Type": "application/json"}
    return {
        "Authorization": f"Key {app_secret}",
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    cfg = _get_config()
    return bool(cfg["app_id"] and cfg["app_secret"])


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify a Pi Network webhook payload using HMAC-SHA256."""
    cfg = _get_config()
    secret = cfg["webhook_secret"]
    if not secret:
        logger.warning("[pi-network] PI_WEBHOOK_SECRET not set — skipping signature check")
        return True
    computed = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


async def get_payment(payment_id: str) -> dict:
    """Fetch payment details from Pi Network API."""
    import httpx
    if not is_configured():
        return {"error": "Pi Network not configured (missing PI_APP_ID or PI_APP_SECRET)"}
    url = f"{_api_base()}/v2/payments/{payment_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_headers())
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"Pi API error {resp.status_code}", "body": resp.text}
    except Exception as exc:
        logger.error("[pi-network] get_payment error: %s", exc)
        return {"error": str(exc)}


async def approve_payment(payment_id: str) -> dict:
    """Server-side approve a Pi payment (call before user confirms on Pi Browser)."""
    import httpx
    if not is_configured():
        return {"error": "Pi Network not configured"}
    url = f"{_api_base()}/v2/payments/{payment_id}/approve"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=_headers(), json={})
        if resp.status_code in (200, 201):
            return {"status": "approved", **resp.json()}
        return {"error": f"Pi API error {resp.status_code}", "body": resp.text}
    except Exception as exc:
        logger.error("[pi-network] approve_payment error: %s", exc)
        return {"error": str(exc)}


async def complete_payment(payment_id: str, txid: str) -> dict:
    """Complete a Pi payment after on-chain confirmation. txid = blockchain transaction hash."""
    import httpx
    if not is_configured():
        return {"error": "Pi Network not configured"}
    url = f"{_api_base()}/v2/payments/{payment_id}/complete"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=_headers(), json={"txid": txid})
        if resp.status_code in (200, 201):
            return {"status": "completed", **resp.json()}
        return {"error": f"Pi API error {resp.status_code}", "body": resp.text}
    except Exception as exc:
        logger.error("[pi-network] complete_payment error: %s", exc)
        return {"error": str(exc)}


async def get_user_info(access_token: str) -> dict:
    """Fetch Pi user info using their access token (from Pi Browser SDK)."""
    import httpx
    url = f"{_api_base()}/v2/me"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_headers(access_token=access_token))
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"Pi API error {resp.status_code}", "body": resp.text}
    except Exception as exc:
        logger.error("[pi-network] get_user_info error: %s", exc)
        return {"error": str(exc)}


async def cancel_payment(payment_id: str) -> dict:
    """Cancel an incomplete Pi payment."""
    import httpx
    if not is_configured():
        return {"error": "Pi Network not configured"}
    url = f"{_api_base()}/v2/payments/{payment_id}/cancel"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=_headers(), json={})
        if resp.status_code in (200, 201):
            return {"status": "cancelled", **resp.json()}
        return {"error": f"Pi API error {resp.status_code}", "body": resp.text}
    except Exception as exc:
        logger.error("[pi-network] cancel_payment error: %s", exc)
        return {"error": str(exc)}
