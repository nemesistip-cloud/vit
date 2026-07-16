"""KYC Verification Service — fully offline, rule-based.

No external API keys. All checks are deterministic and self-contained:
  • Name validation  (2+ words, no digits, plausible length)
  • Age validation   (18–120 years)
  • Doc type check   (known types only)
  • Doc number patterns per type
  • Nationality sanity check
  • Risk scoring (0-100, higher = more risk)
  • Auto-approve / auto-reject / manual_review decision
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timezone, timedelta
from typing import Any

from app.modules.kyc.models import KYCDocumentType, KYCRiskLevel, KYCStatus, KYCSubmission
from sqlalchemy import select

# ── Constants ─────────────────────────────────────────────────────────────────

_MIN_AGE = 18
_MAX_AGE = 120
_AUTO_APPROVE_MAX_RISK = 35
_MANUAL_REVIEW_MAX_RISK = 70  # above this → auto-reject

_DOC_PATTERNS: dict[str, re.Pattern] = {
    KYCDocumentType.PASSPORT:        re.compile(r"^[A-Z]{1,2}[0-9]{6,9}$", re.I),
    KYCDocumentType.NATIONAL_ID:     re.compile(r"^[A-Z0-9]{5,20}$", re.I),
    KYCDocumentType.DRIVERS_LICENSE: re.compile(r"^[A-Z0-9\-]{5,20}$", re.I),
    KYCDocumentType.RESIDENT_PERMIT: re.compile(r"^[A-Z0-9\-]{6,20}$", re.I),
    KYCDocumentType.VOTER_CARD:      re.compile(r"^[A-Z0-9]{8,20}$", re.I),
    KYCDocumentType.BVN:             re.compile(r"^\d{11}$"),
    KYCDocumentType.NIN:             re.compile(r"^\d{11}$"),
}

# Commonly faked / sequential numbers
_FAKE_PATTERNS = [
    re.compile(r"^(.)\1{5,}$"),            # all same char: 111111, aaaaaa
    re.compile(r"^(0123|1234|2345|3456|4567|5678|6789|7890|9876|8765)", re.I),
    re.compile(r"^(test|fake|dummy|sample|xxxx|0000|1111|9999)", re.I),
    re.compile(r"^12345"),
]

_KNOWN_NATIONALITIES = {
    "nigerian", "ghanaian", "kenyan", "south african", "egyptian", "american",
    "british", "canadian", "australian", "german", "french", "italian", "spanish",
    "portuguese", "dutch", "swedish", "norwegian", "danish", "finnish",
    "polish", "russian", "ukrainian", "indian", "pakistani", "bangladeshi",
    "chinese", "japanese", "korean", "indonesian", "malaysian", "filipino",
    "thai", "vietnamese", "brazilian", "argentinian", "colombian", "mexican",
    "peruvian", "chilean", "venezuelan", "turkish", "iranian", "saudi arabian",
    "emirati", "qatari", "kuwaiti", "lebanese", "jordanian", "moroccan",
    "algerian", "tunisian", "ethiopian", "ugandan", "tanzanian", "rwandan",
    "senegalese", "ivorian", "zimbabwean", "zambian", "malawian",
    # short forms too
    "nigeria", "ghana", "kenya", "usa", "uk", "ng", "gh", "ke", "za",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def _parse_dob(dob_str: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(dob_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# ── Rule functions — each returns (passed: bool, risk_delta: int, note: str) ──

def _check_full_name(full_name: str) -> tuple[bool, int, str]:
    name = full_name.strip()
    if not name:
        return False, 40, "full_name is empty"
    if len(name) < 4:
        return False, 30, "full_name too short"
    if len(name) > 150:
        return False, 10, "full_name unusually long"
    if re.search(r"\d", name):
        return False, 25, "full_name contains digits"
    parts = name.split()
    if len(parts) < 2:
        return False, 20, "full_name must have at least 2 words"
    # Check for obviously fake/placeholder names
    fake_names = {"test user", "fake name", "dummy user", "sample name", "test name", "foo bar"}
    if _normalise(name) in fake_names:
        return False, 50, "full_name appears to be a placeholder"
    return True, 0, "ok"


def _check_dob(dob_str: str) -> tuple[bool, int, str]:
    dob = _parse_dob(dob_str)
    if dob is None:
        return False, 30, "date_of_birth format unrecognised (use YYYY-MM-DD)"
    age = _age(dob)
    if age < _MIN_AGE:
        return False, 60, f"applicant is under {_MIN_AGE} years old"
    if age > _MAX_AGE:
        return False, 40, "date_of_birth implies implausible age"
    if dob > date.today():
        return False, 50, "date_of_birth is in the future"
    # Minor risk bump for very young adults
    risk = 10 if age < 21 else 0
    return True, risk, "ok"


def _check_document_type(doc_type: str) -> tuple[bool, int, str]:
    valid = {e.value for e in KYCDocumentType}
    if doc_type not in valid:
        return False, 20, f"document_type '{doc_type}' not recognised"
    return True, 0, "ok"


def _check_document_number(doc_type: str, doc_number: str) -> tuple[bool, int, str]:
    num = doc_number.strip().upper()
    if not num:
        return False, 40, "document_number is empty"
    if len(num) < 4:
        return False, 30, "document_number too short"
    if len(num) > 30:
        return False, 15, "document_number unusually long"

    # Fake / sequential pattern check
    for pat in _FAKE_PATTERNS:
        if pat.match(num):
            return False, 60, "document_number appears fabricated"

    # Doc-type-specific pattern
    pattern = _DOC_PATTERNS.get(doc_type)
    if pattern and not pattern.match(num):
        return True, 15, f"document_number format unusual for {doc_type} (soft fail)"

    return True, 0, "ok"


def _check_nationality(nationality: str) -> tuple[bool, int, str]:
    norm = _normalise(nationality)
    if not norm:
        return False, 20, "nationality is empty"
    if len(norm) < 2:
        return False, 15, "nationality string too short"
    # Loose check — we don't hard-block unknown nationalities, just add risk
    if norm not in _KNOWN_NATIONALITIES:
        return True, 10, f"nationality '{nationality}' not in common list (soft warning)"
    return True, 0, "ok"


# ── Core verification function ─────────────────────────────────────────────────


async def _check_duplicate_id(db, doc_type, doc_number, user_id) -> tuple[bool, int, str]:
    if db is None or user_id is None:
        return True, 0, "skipped (no db context)"

    num = doc_number.strip().upper()
    # Check for other users with same ID number who are already approved
    q = select(KYCSubmission).where(
        KYCSubmission.document_type == doc_type,
        KYCSubmission.document_number == num,
        KYCSubmission.user_id != user_id,
        KYCSubmission.status.in_([KYCStatus.APPROVED, KYCStatus.AUTO_APPROVED])
    )
    res = await db.execute(q)
    existing = res.scalar_one_or_none()
    if existing:
        return False, 80, "document_number already registered to another account"
    return True, 0, "ok"


def _check_liveness(selfie_data: dict | None) -> tuple[bool, int, str]:
    if not selfie_data:
        return False, 50, "selfie/liveness data missing"

    # Simulated advanced check: ensure data structure and minimum "mass"
    image = selfie_data.get("image") or selfie_data.get("video") or selfie_data.get("b64")
    if not image:
        return False, 40, "no image/video found in selfie payload"

    if isinstance(image, str):
        img_len = len(image)
        if img_len < 100:
            return False, 60, "selfie data payload too small (likely empty upload)"
        if img_len < 500:
            return False, 30, "selfie data payload suspiciously small"
        if img_len < 2000:
            return True, 15, "selfie data present but small (low-resolution image?)"

    # Check for liveness signals
    has_metadata = bool(selfie_data.get("metadata"))
    has_timestamp = bool(selfie_data.get("timestamp"))
    has_action = bool(selfie_data.get("action") or selfie_data.get("challenge"))
    liveness_score = selfie_data.get("liveness_score") or selfie_data.get("score")

    if liveness_score is not None:
        try:
            score = float(liveness_score)
            if score < 0.5:
                return False, 35, f"liveness score too low ({score:.2f} < 0.50)"
            if score < 0.7:
                return True, 15, f"liveness score borderline ({score:.2f})"
        except (TypeError, ValueError):
            pass

    if not has_metadata and not has_timestamp:
        return True, 10, "liveness metadata missing (soft warning)"

    if has_action:
        return True, 0, "ok"

    return True, 5, "liveness challenge not recorded (soft warning)"


def _fuzzy_name_similarity(name_a: str, name_b: str) -> float:
    """Simple character-level similarity check between two normalized names."""
    a = _normalise(name_a)
    b = _normalise(name_b)
    if not a or not b:
        return 0.0
    # Common prefix length / max length
    common = sum(ca == cb for ca, cb in zip(a, b))
    return common / max(len(a), len(b))

async def verify_offline(payload: dict[str, Any], db=None, user_id=None) -> dict[str, Any]:
    """
    Run all rule checks and return a structured result:
    {
        status:      "auto_approved" | "manual_review" | "rejected"
        risk_score:  0-100
        risk_level:  "low" | "medium" | "high"
        risk_flags:  ["flag1", ...]
        rule_checks: {"rule_name": {"passed": bool, "note": str}, ...}
    }
    """
    checks: dict[str, dict] = {}
    risk_score = 0
    flags: list[str] = []

    def _run(rule_name: str, result: tuple[bool, int, str]):
        nonlocal risk_score
        passed, delta, note = result
        checks[rule_name] = {"passed": passed, "note": note}
        if not passed:
            risk_score += delta
            flags.append(f"{rule_name}: {note}")
        else:
            risk_score += delta  # may add small risk even on pass

    _run("full_name",       _check_full_name(payload.get("full_name", "")))
    _run("date_of_birth",   _check_dob(payload.get("date_of_birth", "")))
    _run("document_type",   _check_document_type(payload.get("document_type", "")))
    _run("document_number", _check_document_number(
        payload.get("document_type", ""),
        payload.get("document_number", ""),
    ))
    _run("nationality",     _check_nationality(payload.get("nationality", "")))

    # ── Advanced Internal Checks ──
    _run("liveness",        _check_liveness(payload.get("selfie_data")))

    dup_res = await _check_duplicate_id(
        db,
        payload.get("document_type", ""),
        payload.get("document_number", ""),
        user_id
    )
    _run("identity_collision", dup_res)

    # Clamp
    risk_score = min(100, max(0, risk_score))

    # Determine risk level
    if risk_score <= 30:
        risk_level = KYCRiskLevel.LOW
    elif risk_score <= 60:
        risk_level = KYCRiskLevel.MEDIUM
    else:
        risk_level = KYCRiskLevel.HIGH

    # All critical checks must pass for auto-approval
    critical_rules = {"full_name", "date_of_birth", "document_type", "document_number", "liveness", "identity_collision"}
    critical_fail  = any(not checks[r]["passed"] for r in critical_rules if r in checks)

    if critical_fail or risk_score > _MANUAL_REVIEW_MAX_RISK:
        status = KYCStatus.REJECTED
    elif risk_score <= _AUTO_APPROVE_MAX_RISK:
        status = KYCStatus.AUTO_APPROVED
    else:
        status = KYCStatus.MANUAL_REVIEW

    return {
        "status":      status,
        "risk_score":  risk_score,
        "risk_level":  risk_level,
        "risk_flags":  flags,
        "rule_checks": checks,
    }
