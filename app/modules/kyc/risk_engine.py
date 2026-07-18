"""KYC Risk Engine — TRACK-013.

Stateless, deterministic, fully offline. No external API keys required.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# ── Compliance Lists ──────────────────────────────────────────────────────────

RESTRICTED_COUNTRIES: frozenset[str] = frozenset({
    "IR",  # Iran
    "KP",  # North Korea
    "MM",  # Myanmar
    "RU",  # Russia
    "BY",  # Belarus
    "SY",  # Syria
    "CU",  # Cuba
    "VE",  # Venezuela
    "AF",  # Afghanistan
    "YE",  # Yemen
    "LY",  # Libya
    "SD",  # Sudan
    "SO",  # Somalia
    "IQ",  # Iraq
    "CF",  # Central African Republic
    "CD",  # DR Congo
})

INTERNAL_AML_BLOCKLIST: frozenset[str] = frozenset({
    "john doe",
    "jane doe",
    "test user",
    "fake person",
    "dummy account",
    "sample name",
    "aml blocked",
    "sanctioned entity",
    "terror finance",
    "money launderer",
})

# ── Document Validator ────────────────────────────────────────────────────────

_DOC_PATTERNS: dict[str, re.Pattern] = {
    "passport":         re.compile(r"^[A-Z0-9]{6,9}$"),
    "national_id":      re.compile(r"^\d{6,15}$"),
    "drivers_license":  re.compile(r"^[A-Z0-9]{5,16}$"),
    "residence_permit": re.compile(r"^[A-Z0-9]{6,12}$"),
}


class DocumentValidator:
    """Validate document type/number combinations and return a list of violations."""

    def validate(self, doc_type: str, doc_number: str) -> list[str]:
        violations: list[str] = []
        num = (doc_number or "").strip().upper()

        if not num:
            violations.append("document_number is empty")
            return violations

        pattern = _DOC_PATTERNS.get(doc_type)
        if pattern is None:
            # Unknown/unsupported type — flag but don't hard-fail
            violations.append(f"unsupported document_type '{doc_type}'")
            return violations

        if not pattern.match(num):
            violations.append(
                f"document_number '{doc_number}' does not match expected format for {doc_type}"
            )

        # Common fake/sequential patterns
        _FAKE = [
            re.compile(r"^(.)\1{4,}$"),           # aaaaa, 11111
            re.compile(r"^(0123|1234|2345|3456|4567|5678|6789|7890)"),
            re.compile(r"^(TEST|FAKE|DUMMY|SAMPLE|XXXX|0000|9999|1111)", re.I),
            re.compile(r"^12345"),
        ]
        for pat in _FAKE:
            if pat.match(num):
                violations.append("document_number appears fabricated or sequential")
                break

        return violations


# ── Risk Scorer ───────────────────────────────────────────────────────────────

_MINOR_AGE_PENALTY          = 30
_RESTRICTED_COUNTRY_PENALTY = 20
_INVALID_DOC_FORMAT_PENALTY = 15
_NO_SELFIE_PENALTY          = 5
_AML_HIT_PENALTY            = 40


def _normalise(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def _parse_dob(dob_str: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime((dob_str or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class RiskScorer:
    """Compute an integer risk score (0–100) and a list of human-readable flags."""

    def __init__(self) -> None:
        self._validator = DocumentValidator()

    def score(
        self,
        name: str,
        dob: str,
        nationality: str,
        doc_type: str,
        doc_number: str,
        selfie_data: Optional[dict],
    ) -> tuple[int, list[str]]:
        """
        Return (risk_score: int, flags: list[str]).

        Penalties applied:
          • Under-18 applicant          → +30
          • Restricted nationality      → +20
          • Invalid document format     → +15
          • No selfie / liveness data   → +5
          • AML blocklist hit           → +40
        """
        total = 0
        flags: list[str] = []

        # ── Age check ────────────────────────────────────────────────────────
        parsed_dob = _parse_dob(dob)
        if parsed_dob is None:
            total += 15
            flags.append("date_of_birth could not be parsed")
        else:
            age = _age(parsed_dob)
            if age < 18:
                total += _MINOR_AGE_PENALTY
                flags.append(f"applicant is under 18 (age={age})")

        # ── Restricted nationality ────────────────────────────────────────────
        nat_upper = (nationality or "").strip().upper()
        if nat_upper in RESTRICTED_COUNTRIES:
            total += _RESTRICTED_COUNTRY_PENALTY
            flags.append(f"nationality '{nat_upper}' is on FATF restricted list")

        # ── Document format ───────────────────────────────────────────────────
        doc_violations = self._validator.validate(doc_type, doc_number)
        if doc_violations:
            total += _INVALID_DOC_FORMAT_PENALTY
            flags.extend(doc_violations)

        # ── Selfie / liveness ─────────────────────────────────────────────────
        if not selfie_data:
            total += _NO_SELFIE_PENALTY
            flags.append("selfie_data is missing")
        else:
            image = (
                selfie_data.get("image")
                or selfie_data.get("video")
                or selfie_data.get("b64")
            )
            if not image:
                total += _NO_SELFIE_PENALTY
                flags.append("selfie_data payload contains no image or video")

        # ── AML blocklist ─────────────────────────────────────────────────────
        norm_name = _normalise(name or "")
        if norm_name in INTERNAL_AML_BLOCKLIST:
            total += _AML_HIT_PENALTY
            flags.append(f"name '{name}' matched AML internal blocklist")
        else:
            # Partial match — any blocklist token is a full word in the name?
            name_words = set(norm_name.split())
            for entry in INTERNAL_AML_BLOCKLIST:
                entry_words = set(entry.split())
                if entry_words and entry_words.issubset(name_words):
                    total += _AML_HIT_PENALTY
                    flags.append(f"name '{name}' partially matched AML blocklist entry '{entry}'")
                    break

        return min(total, 100), flags


# ── Risk Tier ─────────────────────────────────────────────────────────────────

def risk_tier(score: int) -> str:
    """
    Map a numeric risk score to a named tier.

      0–30  → low           → auto_approved
      31–60 → medium        → manual_review
      61+   → high          → auto_rejected
    """
    if score <= 30:
        return "low"
    if score <= 60:
        return "medium"
    return "high"


def auto_decision_from_tier(tier: str) -> str:
    return {
        "low":    "auto_approved",
        "medium": "manual_review",
        "high":   "auto_rejected",
    }[tier]
