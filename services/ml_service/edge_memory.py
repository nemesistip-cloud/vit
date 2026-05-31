# services/ml_service/edge_memory.py
# VIT Sports Intelligence — Edge Memory System
# Stores profitable betting patterns with ROI tracking + time decay
# Uses the `edges` table via SQLAlchemy (PostgreSQL or SQLite)

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

PATTERN_TYPES = {
    "away_underdog":    {"desc": "Away team is large underdog (>3.0 odds) and wins",  "market": "1x2"},
    "home_steamroller": {"desc": "Elite home team vs lower-tier away",                 "market": "1x2"},
    "high_ou":          {"desc": "High-scoring match (over 2.5 likely)",               "market": "over_under"},
    "low_ou":           {"desc": "Low-scoring match (under 2.5 likely)",               "market": "over_under"},
    "btts_likely":      {"desc": "Both teams likely to score",                         "market": "btts"},
    "no_btts_likely":   {"desc": "Clean sheet likely (one team has weak attack)",      "market": "btts"},
    "draw_underrated":  {"desc": "Market underrates draw probability",                 "market": "1x2"},
    "chaos_match":      {"desc": "Tier-3 chaos match — extreme outcome likely",       "market": "1x2"},
}

MIN_SAMPLE_SIZE = 30
DECAY_THRESHOLD = -0.01
MAX_ACTIVE_PATTERNS = 50

_engine_cache = None


def _get_sync_url() -> str:
    """Convert any database URL (async or sync) to a synchronous SQLAlchemy URL."""
    raw = os.getenv("DATABASE_URL", "sqlite:///./vit.db")

    # Strip async drivers — replace with sync equivalents
    url = raw
    if "sqlite+aiosqlite" in url:
        url = url.replace("sqlite+aiosqlite", "sqlite")
    elif "postgresql+asyncpg" in url or "postgres+asyncpg" in url:
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        url = url.replace("postgres+asyncpg", "postgresql+psycopg2")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # SQLite relative path fix
    if url.startswith("sqlite:///./"):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        db_file = os.path.join(root, url[len("sqlite:///./"):])
        url = f"sqlite:///{db_file}"

    return url


def _get_engine():
    global _engine_cache
    if _engine_cache is None:
        url = _get_sync_url()
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine_cache = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return _engine_cache


class EdgeMemory:
    """
    Persistent edge pattern store backed by the `edges` table.
    Works with both SQLite (dev) and PostgreSQL (production).

    Workflow:
    1. Detect patterns from a batch of simulated/real matches
    2. Store them with initial ROI estimate
    3. Update ROI as more results come in
    4. Apply time decay — stale patterns erode
    5. Archive patterns below ROI threshold
    """

    def __init__(self):
        self.engine = _get_engine()

    # ── Pattern detection from match batch ───────────────────────────────────
    def detect_and_update(self, matches: List[Dict]) -> Dict[str, int]:
        """
        Scan a batch of match dicts for known patterns and update the edge table.
        Returns count of patterns updated per type.
        """
        pattern_buckets: Dict[str, Dict[str, Any]] = {}

        for m in matches:
            result = m.get("result") or m.get("actual_outcome", "")
            ho = m.get("market_odds", {}).get("home", 2.0)
            ao = m.get("market_odds", {}).get("away", 3.0)
            total = m.get("total_goals", 0)
            over25 = m.get("over_25", 0)
            btts = m.get("btts", 0)
            tier = m.get("tier", 1)
            league = m.get("league", "all")
            draw_o = m.get("market_odds", {}).get("draw", 3.3)

            if ao >= 3.0 and result == "A":
                self._bucket_add(pattern_buckets, "away_underdog", league, roi=(ao - 1), hit=True)
            elif ao >= 3.0:
                self._bucket_add(pattern_buckets, "away_underdog", league, roi=-1.0, hit=False)

            if ho <= 1.50 and result == "H":
                self._bucket_add(pattern_buckets, "home_steamroller", league, roi=(ho - 1), hit=True)
            elif ho <= 1.50:
                self._bucket_add(pattern_buckets, "home_steamroller", league, roi=-1.0, hit=False)

            if over25:
                self._bucket_add(pattern_buckets, "high_ou", league, roi=0.88, hit=True)
            else:
                self._bucket_add(pattern_buckets, "high_ou", league, roi=-1.0, hit=False)
                self._bucket_add(pattern_buckets, "low_ou", league, roi=0.85, hit=True)

            if btts:
                self._bucket_add(pattern_buckets, "btts_likely", league, roi=0.80, hit=True)
            else:
                self._bucket_add(pattern_buckets, "btts_likely", league, roi=-1.0, hit=False)
                self._bucket_add(pattern_buckets, "no_btts_likely", league, roi=0.75, hit=True)

            if result == "D" and draw_o >= 3.5:
                self._bucket_add(pattern_buckets, "draw_underrated", league, roi=(draw_o - 1), hit=True)
            elif draw_o >= 3.5:
                self._bucket_add(pattern_buckets, "draw_underrated", league, roi=-1.0, hit=False)

            if tier == 3:
                if result in ("H", "A") and total >= 4:
                    self._bucket_add(pattern_buckets, "chaos_match", league, roi=1.20, hit=True)
                else:
                    self._bucket_add(pattern_buckets, "chaos_match", league, roi=-1.0, hit=False)

        updated = {}
        for ptype, stats in pattern_buckets.items():
            count = self._upsert_pattern(ptype, stats)
            updated[ptype] = count

        return updated

    @staticmethod
    def _bucket_add(buckets: Dict, ptype: str, league: str, roi: float, hit: bool):
        if ptype not in buckets:
            buckets[ptype] = {"league": league, "rois": [], "hits": 0, "total": 0}
        buckets[ptype]["rois"].append(roi)
        buckets[ptype]["total"] += 1
        if hit:
            buckets[ptype]["hits"] += 1

    def _upsert_pattern(self, ptype: str, stats: Dict) -> int:
        rois = stats["rois"]
        if not rois:
            return 0

        avg_roi = sum(rois) / len(rois)
        league = stats["league"]
        meta = PATTERN_TYPES.get(ptype, {})
        desc = meta.get("desc", ptype)
        market = meta.get("market", "1x2")
        now = datetime.now(timezone.utc)
        sample_add = len(rois)
        edge_id = f"{ptype}_{league}"

        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT edge_id, roi, sample_size FROM edges WHERE edge_id = :eid"),
                {"eid": edge_id}
            ).mappings().fetchone()

            if row:
                old_roi = row["roi"]
                old_n = row["sample_size"]
                new_n = old_n + sample_add
                blended_roi = (old_roi * old_n + avg_roi * sample_add) / new_n
                conn.execute(
                    text("""
                        UPDATE edges
                        SET roi = :roi, sample_size = :n, last_updated = :now, status = 'active'
                        WHERE edge_id = :eid
                    """),
                    {"roi": round(blended_roi, 4), "n": new_n, "now": now, "eid": edge_id}
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO edges
                            (edge_id, description, roi, sample_size, confidence, avg_edge,
                             league, market, status, decay_rate, created_at, last_updated)
                        VALUES
                            (:eid, :desc, :roi, :n, :conf, :avg_edge,
                             :league, :market, 'active', 0.03, :now, :now)
                    """),
                    {
                        "eid": edge_id,
                        "desc": desc,
                        "roi": round(avg_roi, 4),
                        "n": sample_add,
                        "conf": round(min(0.9, sample_add / 1000), 3),
                        "avg_edge": round(avg_roi, 4),
                        "league": league,
                        "market": market,
                        "now": now,
                    }
                )

        return sample_add

    # ── Apply time decay ─────────────────────────────────────────────────────
    def apply_decay(self, days_elapsed: float = 1.0) -> Dict[str, int]:
        """Reduce ROI of all active patterns and archive those below threshold."""
        now = datetime.now(timezone.utc)
        archived = 0
        decayed = 0

        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT edge_id, roi, decay_rate, sample_size FROM edges WHERE status = 'active'")
            ).mappings().fetchall()

            for row in rows:
                new_roi = row["roi"] - row["decay_rate"] * days_elapsed
                if new_roi < DECAY_THRESHOLD or (row["sample_size"] >= MIN_SAMPLE_SIZE and new_roi < -0.02):
                    conn.execute(
                        text("UPDATE edges SET status = 'archived', archived_at = :now, roi = :roi WHERE edge_id = :eid"),
                        {"now": now, "roi": round(new_roi, 4), "eid": row["edge_id"]}
                    )
                    archived += 1
                else:
                    conn.execute(
                        text("UPDATE edges SET roi = :roi, last_updated = :now WHERE edge_id = :eid"),
                        {"roi": round(new_roi, 4), "now": now, "eid": row["edge_id"]}
                    )
                    decayed += 1

        return {"decayed": decayed, "archived": archived}

    # ── Get active edges ─────────────────────────────────────────────────────
    def get_active(self, min_sample: int = MIN_SAMPLE_SIZE, limit: int = MAX_ACTIVE_PATTERNS) -> List[Dict]:
        """Return active edge patterns sorted by ROI descending."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT * FROM edges
                    WHERE status = 'active' AND sample_size >= :min_s
                    ORDER BY roi DESC
                    LIMIT :lim
                """),
                {"min_s": min_sample, "lim": limit}
            ).mappings().fetchall()
        return [dict(r) for r in rows]

    # ── Summary stats ────────────────────────────────────────────────────────
    def summary(self) -> Dict[str, Any]:
        with self.engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM edges")).scalar() or 0
            active = conn.execute(text("SELECT COUNT(*) FROM edges WHERE status = 'active'")).scalar() or 0
            archived = conn.execute(text("SELECT COUNT(*) FROM edges WHERE status = 'archived'")).scalar() or 0
            top_rows = conn.execute(
                text("SELECT edge_id, roi, sample_size FROM edges WHERE status = 'active' ORDER BY roi DESC LIMIT 5")
            ).mappings().fetchall()

        return {
            "total_patterns": total,
            "active": active,
            "archived": archived,
            "top_edges": [dict(r) for r in top_rows],
        }

    # ── Prune excess patterns ────────────────────────────────────────────────
    def prune(self, keep: int = MAX_ACTIVE_PATTERNS) -> int:
        """Archive lowest-ROI active patterns if total exceeds the keep limit."""
        now = datetime.now(timezone.utc)
        with self.engine.begin() as conn:
            active_count = conn.execute(
                text("SELECT COUNT(*) FROM edges WHERE status = 'active'")
            ).scalar() or 0

            if active_count <= keep:
                return 0

            excess = active_count - keep
            conn.execute(
                text("""
                    UPDATE edges SET status = 'archived', archived_at = :now
                    WHERE edge_id IN (
                        SELECT edge_id FROM edges
                        WHERE status = 'active'
                        ORDER BY roi ASC
                        LIMIT :excess
                    )
                """),
                {"now": now, "excess": excess}
            )
        return excess
