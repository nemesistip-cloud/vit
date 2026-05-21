"""Smile Identity v2 ID Verification integration.

Called when SMILE_IDENTITY_API_KEY + SMILE_IDENTITY_PARTNER_ID are both set.
Falls back to offline engine when either is missing.

Docs: https://docs.smileidentity.com/server-to-server/id-verification
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import (
    SMILE_IDENTITY_API_KEY,
    SMILE_IDENTITY_PARTNER_ID,
    SMILE_IDENTITY_SANDBOX,
)

import httpx

from app.modules.kyc.models import KYCRiskLevel, KYCStatus

logger = logging.getLogger(__name__)

_SANDBOX_URL    = "https://testapi.smileidentity.com/v1/id_verification"
_PRODUCTION_URL = "https://api.smileidentity.com/v1/id_verification"

_NATIONALITY_TO_COUNTRY: dict[str, str] = {
    "nigerian": "NG", "nigeria": "NG", "ng": "NG",
    "ghanaian": "GH", "ghana": "GH", "gh": "GH",
    "kenyan": "KE", "kenya": "KE", "ke": "KE",
    "south african": "ZA", "za": "ZA",
    "ugandan": "UG", "tanzanian": "TZ", "rwandan": "RW",
    "senegalese": "SN", "ivorian": "CI", "ethiopian": "ET",
    "egyptian": "EG", "moroccan": "MA", "algerian": "DZ",
    "american": "US", "usa": "US",
    "british": "GB", "uk": "GB",
    "canadian": "CA", "australian": "AU",
    "german": "DE", "french": "FR", "italian": "IT",
    "spanish": "ES", "portuguese": "PT", "dutch": "NL",
    "indian": "IN", "pakistani": "PK", "bangladeshi": "BD",
    "chinese": "CN", "japanese": "JP", "korean": "KR",
    "indonesian": "ID", "malaysian": "MY", "filipino": "PH",
    "thai": "TH", "vietnamese": "VN",
    "brazilian": "BR", "argentinian": "AR", "colombian": "CO",
    "mexican": "MX", "peruvian": "PE", "chilean": "CL",
    "turkish": "TR", "iranian": "IR", "saudi arabian": "SA",
    "emirati": "AE", "qatari": "QA",
    "zimbabwean": "ZW", "zambian": "ZM",
}

_DOC_TYPE_MAP: dict[str, str] = {
    "passport":        "PASSPORT",
    "national_id":     "NATIONAL_ID",
    "drivers_license": "DRIVERS_LICENSE",
    "voter_card":      "VOTER_ID",
    "bvn":             "BVN",
    "nin":             "NIN",
    "resident_permit": "RESIDENT_PERMIT",
}


def _is_configured() -> tuple[bool, str, str]:
    """Return (configured, api_key, partner_id)."""
    api_key = SMILE_IDENTITY_API_KEY.strip()
    partner_id = SMILE_IDENTITY_PARTNER_ID.strip()
    return bool(api_key and partner_id), api_key, partner_id


def _build_signature(api_key: str, partner_id: str, timestamp: str) -> str:
    """HMAC-SHA256 signature: base64(HMAC(timestamp + partner_id, api_key))."""
    to_sign = (timestamp + partner_id).encode()
    raw = hmac.new(api_key.encode(), to_sign, hashlib.sha256).digest()
    return base64.b64encode(raw).decode()


def _nationality_to_country(nationality: str) -> str:
    """Convert a nationality string to an ISO 3166-1 alpha-2 code (best-effort)."""
    key = nationality.strip().lower()
    return _NATIONALITY_TO_COUNTRY.get(key, "NG")


async def verify_with_smile_identity(payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Call the Smile Identity ID Verification endpoint.

    Returns a structured result dict compatible with verify_offline(), or None
    if the integration is not configured or the call fails (caller should fall back
    to offline engine).
    """
    configured, api_key, partner_id = _is_configured()
    if not configured:
        return None

    sandbox = SMILE_IDENTITY_SANDBOX
    url = _SANDBOX_URL if sandbox else _PRODUCTION_URL

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    signature = _build_signature(api_key, partner_id, timestamp)

    full_name     = payload.get("full_name", "")
    name_parts    = full_name.strip().split()
    first_name    = name_parts[0] if name_parts else ""
    last_name     = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    nationality   = payload.get("nationality", "")
    country       = _nationality_to_country(nationality)
    doc_type_raw  = payload.get("document_type", "")
    id_type       = _DOC_TYPE_MAP.get(doc_type_raw, "NATIONAL_ID")
    id_number     = payload.get("document_number", "")
    dob           = payload.get("date_of_birth", "")

    body = {
        "source_sdk":         "rest_api",
        "source_sdk_version": "1.0.0",
        "partner_id":         partner_id,
        "signature":          signature,
        "timestamp":          timestamp,
        "country":            country,
        "id_type":            id_type,
        "id_number":          id_number,
        "first_name":         first_name,
        "last_name":          last_name,
        "dob":                dob,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=body)
            data = resp.json()
    except Exception as exc:
        logger.warning("[smile-identity] API call failed: %s — falling back to offline", exc)
        return None

    logger.info("[smile-identity] response code=%s result_code=%s", resp.status_code, data.get("ResultCode"))

    result_code = str(data.get("ResultCode", ""))
    result_text = data.get("ResultText", "")
    actions     = data.get("Actions", {})

    verify_action = actions.get("Verify_ID_Number", "")

    if result_code in ("1012", "1013") and verify_action == "Verified":
        # Exact or partial match → auto-approve with low risk
        risk_score = 10 if result_code == "1012" else 20
        return {
            "status":      KYCStatus.AUTO_APPROVED,
            "risk_score":  risk_score,
            "risk_level":  KYCRiskLevel.LOW,
            "risk_flags":  [],
            "rule_checks": {
                "smile_identity": {
                    "passed": True,
                    "note": f"ResultCode={result_code} ({result_text})",
                }
            },
        }

    if result_code == "1014":
        # ID not found in database → manual review
        return {
            "status":      KYCStatus.MANUAL_REVIEW,
            "risk_score":  55,
            "risk_level":  KYCRiskLevel.MEDIUM,
            "risk_flags":  ["ID not found in identity database"],
            "rule_checks": {
                "smile_identity": {
                    "passed": False,
                    "note": f"ResultCode={result_code} — ID not found ({result_text})",
                }
            },
        }

    if result_code == "1015":
        # DOB mismatch → manual review
        return {
            "status":      KYCStatus.MANUAL_REVIEW,
            "risk_score":  45,
            "risk_level":  KYCRiskLevel.MEDIUM,
            "risk_flags":  ["Date of birth mismatch"],
            "rule_checks": {
                "smile_identity": {
                    "passed": False,
                    "note": f"ResultCode={result_code} — DOB mismatch ({result_text})",
                }
            },
        }

    # Any other code (errors, unknown) → fall back to offline
    logger.warning(
        "[smile-identity] unhandled result code=%s text=%s — falling back to offline",
        result_code, result_text,
    )
    return None
