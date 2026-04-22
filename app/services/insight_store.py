import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INSIGHTS_DIR = os.path.join(ROOT_DIR, "data", "insights")

PROVIDERS = ("gemini", "claude", "grok")
PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "claude": "Anthropic Claude",
    "grok": "xAI Grok",
}


def _safe_match_id(match_id: int) -> str:
    return re.sub(r"[^0-9]", "", str(match_id))


def _path_for(match_id: int) -> str:
    return os.path.join(INSIGHTS_DIR, f"match_{_safe_match_id(match_id)}.json")


def _as_probability(value: Any, fallback: Optional[float] = None) -> Optional[float]:
    if value is None:
        return fallback
    try:
        numeric = float(value)
        if numeric > 1:
            numeric = numeric / 100
        return max(0.0, min(1.0, numeric))
    except Exception:
        return fallback


def normalize_provider_insight(source: str, payload: Dict[str, Any], defaults: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    defaults = defaults or {}
    source = str(source).lower().strip()
    home_prob = _as_probability(payload.get("home_prob", payload.get("home")), defaults.get("home_prob"))
    draw_prob = _as_probability(payload.get("draw_prob", payload.get("draw")), defaults.get("draw_prob"))
    away_prob = _as_probability(payload.get("away_prob", payload.get("away")), defaults.get("away_prob"))
    confidence = _as_probability(payload.get("confidence"), defaults.get("confidence", 0.7))
    risk_level = str(payload.get("risk_level") or payload.get("risk") or "MEDIUM").upper()
    if risk_level not in {"LOW", "MEDIUM", "HIGH"}:
        risk_level = "MEDIUM"

    return {
        "available": True,
        "source": source,
        "label": payload.get("label") or PROVIDER_LABELS.get(source, source.title()),
        "home_prob": home_prob,
        "draw_prob": draw_prob,
        "away_prob": away_prob,
        "confidence": confidence,
        "summary": payload.get("summary") or payload.get("analysis") or "",
        "key_factors": payload.get("key_factors") or payload.get("factors") or [],
        "value_assessment": payload.get("value_assessment") or payload.get("value") or "",
        "risk_level": risk_level,
        "insight_tags": payload.get("insight_tags") or payload.get("tags") or [],
        "error": None,
        "from_cache": True,
    }


def _extract_insights(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    candidates = raw.get("insights") or raw.get("agents") or raw.get("results") or raw.get("providers") or raw
    if not isinstance(candidates, dict):
        return {}

    extracted = {}
    for source in PROVIDERS:
        value = candidates.get(source)
        if isinstance(value, dict):
            extracted[source] = value
    return extracted


def save_match_insights(match_id: int, raw: Dict[str, Any]) -> Dict[str, Any]:
    insights = _extract_insights(raw)
    if not insights:
        raise ValueError("JSON must include insights for at least one provider: gemini, claude, or grok")

    os.makedirs(INSIGHTS_DIR, exist_ok=True)
    payload = {
        "match_id": match_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "insights": insights,
        "original": raw,
    }
    path = _path_for(match_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return {"match_id": match_id, "path": path, "sources": sorted(insights.keys()), "count": len(insights)}


def load_match_insights(match_id: int, defaults: Optional[Dict[str, float]] = None) -> Dict[str, Dict[str, Any]]:
    path = _path_for(match_id)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    insights = _extract_insights(raw)
    return {
        source: normalize_provider_insight(source, payload, defaults=defaults)
        for source, payload in insights.items()
    }


def infer_match_id(raw: Dict[str, Any]) -> Optional[int]:
    value = raw.get("match_id") or raw.get("id")
    try:
        return int(value) if value is not None else None
    except Exception:
        return None