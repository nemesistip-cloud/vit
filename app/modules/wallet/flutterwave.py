"""app/modules/wallet/flutterwave.py — Flutterwave payment integration.

Supports:
  - Mobile Money deposits (MTN, Airtel, M-Pesa, Tigo)
  - Card / bank transfer deposits
  - Bank account withdrawals via Transfer API
  - Webhook signature verification

Currencies supported: NGN, GHS, KES, UGX, TZS (MoMo networks vary by country)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

# Country → default MoMo network mapping
COUNTRY_MOMO_NETWORKS = {
    "NG": "mtn",
    "GH": "mtn",
    "KE": "mpesa",
    "UG": "mtn",
    "TZ": "mtn",
    "CM": "mtn",
    "CI": "mtn",
    "SN": "free",
    "ZM": "mtn",
    "RW": "mtn",
}

CURRENCY_COUNTRY = {
    "NGN": "NG",
    "GHS": "GH",
    "KES": "KE",
    "UGX": "UG",
    "TZS": "TZ",
}


def _get_flw_key() -> str:
    from app.config import FLW_SECRET_KEY
    return FLW_SECRET_KEY or os.getenv("FLW_SECRET_KEY", "")


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Flutterwave webhook using HMAC-SHA256 of raw body."""
    from app.config import FLW_WEBHOOK_SECRET
    secret = FLW_WEBHOOK_SECRET or os.getenv("FLW_WEBHOOK_SECRET", "")
    if not secret:
        return True  # allow-through when not configured
    computed = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


async def initiate_momo_deposit(
    amount: float,
    currency: str,
    phone_number: str,
    network: Optional[str],
    email: str,
    reference: str,
    redirect_url: str = "",
) -> dict:
    """Initiate a Mobile Money charge via Flutterwave Charges API."""
    import httpx

    flw_key = _get_flw_key()
    if not flw_key:
        return {"error": "Flutterwave not configured", "payment_link": None}

    country = CURRENCY_COUNTRY.get(currency.upper(), "NG")
    net = network or COUNTRY_MOMO_NETWORKS.get(country, "mtn")

    payload = {
        "amount": amount,
        "currency": currency.upper(),
        "email": email,
        "phone_number": phone_number,
        "network": net,
        "tx_ref": reference,
        "fullname": email.split("@")[0],
        "redirect_url": redirect_url or "https://vitnetwork.app/wallet?deposit=momo",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.flutterwave.com/v3/charges?type=mobile_money_" + country.lower(),
                headers={
                    "Authorization": f"Bearer {flw_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        data = resp.json()
        if data.get("status") == "success":
            meta = data.get("meta", {})
            return {
                "status": "pending",
                "payment_link": meta.get("authorization", {}).get("redirect") or meta.get("redirect"),
                "flw_ref": data.get("data", {}).get("flw_ref"),
                "raw": data,
            }
        return {"error": data.get("message", "Flutterwave error"), "payment_link": None, "raw": data}
    except Exception as exc:
        logger.error("[flutterwave] initiate_momo_deposit error: %s", exc)
        return {"error": str(exc), "payment_link": None}


async def initiate_bank_transfer_deposit(
    amount: float,
    currency: str,
    email: str,
    reference: str,
) -> dict:
    """Create a temporary virtual bank account for deposit."""
    import httpx

    flw_key = _get_flw_key()
    if not flw_key:
        return {"error": "Flutterwave not configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.flutterwave.com/v3/virtual-account-numbers",
                headers={"Authorization": f"Bearer {flw_key}"},
                json={
                    "email": email,
                    "is_permanent": False,
                    "bvn": "",
                    "tx_ref": reference,
                    "amount": amount,
                    "currency": currency.upper(),
                    "narration": f"VIT deposit {reference}",
                    "frequency": 1,
                },
            )
        data = resp.json()
        if data.get("status") == "success":
            return {
                "status": "pending",
                "account_number": data["data"].get("account_number"),
                "bank_name": data["data"].get("bank_name"),
                "account_name": data["data"].get("account_name"),
                "amount": amount,
                "expires_at": data["data"].get("expiry_date"),
            }
        return {"error": data.get("message", "Flutterwave error")}
    except Exception as exc:
        logger.error("[flutterwave] bank_transfer_deposit error: %s", exc)
        return {"error": str(exc)}


async def execute_momo_withdrawal(
    amount: float,
    currency: str,
    account_bank: str,
    account_number: str,
    beneficiary_name: str,
    reference: str,
    narration: str = "VIT withdrawal",
) -> dict:
    """Execute a withdrawal to a mobile money or bank account via Flutterwave Transfer API."""
    import httpx

    flw_key = _get_flw_key()
    if not flw_key:
        return {"error": "Flutterwave not configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.flutterwave.com/v3/transfers",
                headers={"Authorization": f"Bearer {flw_key}"},
                json={
                    "account_bank": account_bank,
                    "account_number": account_number,
                    "amount": amount,
                    "currency": currency.upper(),
                    "reference": reference,
                    "narration": narration,
                    "beneficiary_name": beneficiary_name,
                },
            )
        data = resp.json()
        if data.get("status") == "success":
            return {
                "status": "success",
                "transfer_id": data["data"].get("id"),
                "reference": reference,
            }
        return {"error": data.get("message", "Transfer failed"), "raw": data}
    except Exception as exc:
        logger.error("[flutterwave] execute_momo_withdrawal error: %s", exc)
        return {"error": str(exc)}


async def verify_transaction(tx_id: str) -> dict:
    """Verify a Flutterwave transaction by ID."""
    import httpx

    flw_key = _get_flw_key()
    if not flw_key:
        return {"error": "Flutterwave not configured"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.flutterwave.com/v3/transactions/{tx_id}/verify",
                headers={"Authorization": f"Bearer {flw_key}"},
            )
        data = resp.json()
        return data
    except Exception as exc:
        logger.error("[flutterwave] verify_transaction error: %s", exc)
        return {"error": str(exc)}
